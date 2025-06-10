import os
import numpy as np
import asyncio
from queue import Queue
from datetime import datetime, timedelta
import speech_recognition as sr
from geminiClient import live
import torch
import keyHandler
from dotenv import load_dotenv
import websockets
from constants import DB_PATH, YAML_FILE_PATH, ASSISTANT_NAME

load_dotenv()

data_queue = Queue()
transcription = ['']
phrase_time = None
phrase_bytes = bytes()

keyHandler.openConn(DB_PATH)
keyHandler.loadKeysData(YAML_FILE_PATH)
apiKeyId: str = keyHandler.getKeyId()
print(f"Using key: {apiKeyId}")

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

async def conversation_loop(audio_model, recognizer, mic, phrase_timeout, record_timeout):
    global phrase_time, phrase_bytes, transcription, apiKeyId

    stop_listening = recognizer.listen_in_background(mic, record_callback, phrase_time_limit=record_timeout)
    print("Model loaded. Listening...\n")

    while True:
        now = datetime.utcnow()
        phrase_complete = False

        if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
            phrase_bytes = bytes()
            phrase_time = None
            phrase_complete = True

        if not data_queue.empty() or phrase_complete:
            text = ""
            if not phrase_complete:
                phrase_time = now
                audio_data = b''.join(data_queue.queue)
                data_queue.queue.clear()
                phrase_bytes += audio_data
                audio_np = np.frombuffer(phrase_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available())
                text = result['text'].strip()

            if phrase_complete:
                transcription.append(text + " <--- end")

                prompt = transcription[-2]
                if prompt.find(ASSISTANT_NAME) >= 0:
                    prompt = prompt.replace(ASSISTANT_NAME, "", 1)

                    print("Paused. Waiting for reply...")
                    stop_listening(wait_for_stop=False)

                    while True:
                        try:
                            await live(prompt, os.getenv(apiKeyId))

                        except websockets.exceptions.ConnectionClosedError as e:
                            print("An error has occured, changing key")
                            keyHandler.insertKeyLog(apiKeyId, False, e.code)
                            apiKeyId = keyHandler.getNextKeyId(apiKeyId)
                            print(f"new keyId: {apiKeyId}")
                            
                        else:
                            keyHandler.insertKeyLog(apiKeyId, True, None)
                            break

                    print("Resumed listening...\n")
                    stop_listening = recognizer.listen_in_background(mic, record_callback, phrase_time_limit=record_timeout)
            else:
                transcription[-1] = text

            # os.system('cls' if os.name == 'nt' else 'clear')
            for line in transcription:
                print(line)
        else:
            await asyncio.sleep(0.25)
