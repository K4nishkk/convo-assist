import numpy as np
import asyncio
from queue import Queue
from datetime import datetime, timedelta
import speech_recognition as sr
import torch
from dotenv import load_dotenv
import websockets
from constants import *
import logging
import geminiClient, keyManager
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)

load_dotenv()

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
        phrase_complete = False

        if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
            phrase_bytes = bytes()
            phrase_time = None
            phrase_complete = True

        if not data_queue.empty():
            text = ""
            phrase_time = now
            audio_data = b''.join(data_queue.queue)
            data_queue.queue.clear()
            phrase_bytes += audio_data
            audio_np = np.frombuffer(phrase_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available())
            text = result['text'].strip()
            transcription[-1] = text

        if phrase_complete:
            transcription.append("") # append blank text

            prompt = transcription[-2]
            if prompt.find(ASSISTANT_NAME) >= 0:
                prompt = prompt.replace(ASSISTANT_NAME, "", 1)

                logging.info("Paused. Waiting for reply...")
                stop_listening(wait_for_stop=False)

                try:
                    start = time.perf_counter()
                    total_bytes, key_id = await streamer.send_prompt(prompt)
                    end = time.perf_counter()

                    audio_duration = total_bytes / (AUDIO_RATE * AUDIO_CHANNELS * 2)
                    effective_response_time = (end - start) - audio_duration

                    # logging.info(f"audio_duration: {audio_duration}")
                    # logging.info(f"effective_response_time {effective_response_time}")

                    # TODO wrong key getting inserted after restarting connection
                    asyncio.create_task(db.insertKeyLog(key_id=key_id, total_bytes=total_bytes, audio_duration=audio_duration, lag=effective_response_time))

                except websockets.exceptions.ConnectionClosedError as e:
                    logging.error(e)
                    asyncio.create_task(db.insertKeyLog(key_id=key_id, success=False, error=e.code))
                    raise e

                logging.info("Resumed listening...\n")
                stop_listening = recognizer.listen_in_background(mic, record_callback, phrase_time_limit=record_timeout)
            else:
                logging.info(f"Prompt (not dispatched): {prompt}")
        else:
            await asyncio.sleep(0.25)
