from google import genai
from google.genai import types
import pyaudio
import asyncio
import websockets

import time
import os
from dotenv import load_dotenv
load_dotenv()

# PyAudio configuration
RATE = 24000
CHANNELS = 1
FORMAT = pyaudio.paInt16

model = "gemini-2.5-flash-preview-native-audio-dialog"
config = types.LiveConnectConfig(response_modalities=[types.Modality.AUDIO])

async def live(message, api_key):
    # performance measuring vars
    begin_time = time.perf_counter()
    first_audio_time = None
    total_bytes = 0
    lag = None
    audio_duration = None

    client = genai.Client(api_key=api_key)

    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True,
        frames_per_buffer=1024,
        stream_callback=None
    )

    try:
        async with client.aio.live.connect(model=model, config=config) as session:

            await session.send_client_content(turns={"role": "user", "parts": [{"text": message}]}, turn_complete=True)
            print(f"message sent: {message}, awaiting response")

            async for response in session.receive():
                if response.data:
                    if first_audio_time is None:
                        first_audio_time = time.perf_counter()
                        lag = first_audio_time - begin_time

                    chunk_size = len(response.data)
                    total_bytes += chunk_size
                    stream.write(response.data)

        audio_duration = total_bytes / (RATE * CHANNELS * 2)

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Code: {e.code}")
        print(f"Reason: {e.reason}")
        raise e

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

        print(f"Lag: {lag}")
        print(f"total_bytes: {total_bytes}")
        print(f"audio_duration {audio_duration}")
        
        return lag, total_bytes, audio_duration

if __name__ == "__main__":
    asyncio.run(live("how are you", os.getenv("API_KEY8")))