import whisper
import sounddevice as sd
import numpy as np
import queue

model = whisper.load_model("base")
q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(indata.copy())

# 16000 Hz sample rate (as Whisper expects)
with sd.InputStream(samplerate=16000, channels=1, callback=callback):
    print("Speak into the microphone...")
    while True:
        audio = q.get()
        audio = np.squeeze(audio)
        result = model.transcribe(audio, language='en', fp16=False)
        print("You said:", result["text"])
