import whisper
import sounddevice as sd
import numpy as np

model = whisper.load_model("base")  # or "small", "medium", etc.

# Recording settings
duration = 5  # seconds
sample_rate = 16000  # Whisper expects 16kHz input

print("🎤 Listening... Speak now!")

# Record audio
recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
sd.wait()  # Wait until recording is finished

# Convert to numpy array and transcribe
audio = np.squeeze(recording)
result = model.transcribe(audio, fp16=False)

# Display transcription
print("📝 You said:", result['text'])
