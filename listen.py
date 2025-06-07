import argparse
import os
import numpy as np
import speech_recognition as sr
import whisper
import torch
import asyncio

from datetime import datetime, timedelta
from queue import Queue
from time import sleep
from sys import platform
from whisper_server import start_websocket, broadcast

# Global queue and transcription state
data_queue = Queue()
transcription = ['']
phrase_time = None
phrase_bytes = bytes()

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--non_english", action='store_true')
    parser.add_argument("--energy_threshold", default=1000, type=int)
    parser.add_argument("--record_timeout", default=2, type=float)
    parser.add_argument("--phrase_timeout", default=3, type=float)
    if 'linux' in platform:
        parser.add_argument("--default_microphone", default='pulse', type=str)
    return parser.parse_args()

def setup_microphone(args):
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = args.energy_threshold
    recognizer.dynamic_energy_threshold = False
    mic = sr.Microphone(sample_rate=16000)
    with mic:
        recognizer.adjust_for_ambient_noise(mic)
    return recognizer, mic

def record_callback(_, audio: sr.AudioData):
    data = audio.get_raw_data()
    data_queue.put(data)

async def transcribe_loop(audio_model, recognizer, mic, phrase_timeout, record_timeout):
    global phrase_time, phrase_bytes, transcription
    recognizer.listen_in_background(mic, record_callback, phrase_time_limit=record_timeout)
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
                await broadcast(transcription[-2])
            else:
                transcription[-1] = text

            os.system('cls' if os.name == 'nt' else 'clear')
            for line in transcription:
                print(line)
        else:
            await asyncio.sleep(0.25)

async def main():
    args = setup_args()
    model_name = args.model + ("" if args.non_english else ".en")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    recognizer, mic = setup_microphone(args)
    audio_model = whisper.load_model(model_name).to(device)

    # Start WebSocket server
    await start_websocket()

    # Run transcription loop
    await transcribe_loop(audio_model, recognizer, mic, args.phrase_timeout, args.record_timeout)

if __name__ == "__main__":
    asyncio.run(main())