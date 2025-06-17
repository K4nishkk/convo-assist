import numpy as np
import asyncio
from queue import Queue
from datetime import datetime, timedelta
import speech_recognition as sr
import websockets
from utils.constants import ASSISTANT_NAME
import core.geminiClient as geminiClient, utils.keyManager as keyManager
import time

from dotenv import load_dotenv
load_dotenv()

import logging
logger = logging.getLogger(__name__)

data_queue = Queue()
transcription = ['']
phrase_time = None
phrase_bytes = bytes()

def setup_microphone(energy_threshold):
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = energy_threshold
    recognizer.dynamic_energy_threshold = False
    mic = sr.Microphone(sample_rate=16000)
    with mic:
        recognizer.adjust_for_ambient_noise(mic)
    return recognizer, mic

def record_callback(_, audio: sr.AudioData):
    data = audio.get_raw_data()
    data_queue.put(data)

async def conversation_loop(
    audio_model,
    recognizer,
    mic,
    phrase_timeout,
    record_timeout,
    db: keyManager.KeyManager,
    streamer: geminiClient.GeminiSession,
    key_id: str # inital key_id, used for setting connection first time
):
    global phrase_time, phrase_bytes, transcription
    stop_listening = recognizer.listen_in_background(mic, record_callback, phrase_time_limit=record_timeout)
    logging.info("Model loaded. Listening...\n")

    while True:
        now = datetime.utcnow()

        if phrase_complete(now, phrase_time, phrase_timeout):
            phrase_bytes = bytes()
            phrase_time = None

            prompt = transcription[-1]
            transcription.append("")

            if prompt.find(ASSISTANT_NAME) >= 0:
                prompt = prompt.replace(ASSISTANT_NAME, "", 1)

                logging.info("Paused. Waiting for reply...")
                stop_listening(wait_for_stop=False)

                try:
                    start = time.perf_counter()
                    total_bytes, key_id = await streamer.send_prompt(prompt)
                    end = time.perf_counter()

                    db.insertKeyLog(key_id=key_id, total_bytes=total_bytes, total_duration=(end - start))

                except websockets.exceptions.ConnectionClosedError as e:
                    logging.error(e)
                    db.insertKeyLog(key_id=key_id, success=False, error=e.code)

                logging.info("Resumed listening...\n")
                stop_listening = recognizer.listen_in_background(mic, record_callback, phrase_time_limit=record_timeout)

            elif len(prompt) > 10:
                logging.info(f"Prompt (not dispatched): {prompt[:10]}...")

        if not data_queue.empty():
            text = ""
            phrase_time = now
            audio_data = b''.join(data_queue.queue)
            data_queue.queue.clear()
            phrase_bytes += audio_data
            audio_np = np.frombuffer(phrase_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            segments, info = audio_model.transcribe(audio_np)
            text = "".join([s.text for s in segments])
            print(text)
            transcription[-1] = text

        else:
            await asyncio.sleep(0.25)

def phrase_complete(now, phrase_time, phrase_timeout):
    return phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout)