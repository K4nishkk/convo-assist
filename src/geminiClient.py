from google import genai
from google.genai import types
import pyaudio
import asyncio
import keyManager
import logging
import time
import os
from dotenv import load_dotenv
import websockets

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)

# PyAudio configuration
RATE = 24000
CHANNELS = 1
FORMAT = pyaudio.paInt16

model = "gemini-2.5-flash-preview-native-audio-dialog"
config = types.LiveConnectConfig(
    response_modalities=[types.Modality.AUDIO],
    context_window_compression=(
        types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        )
    )
)

class GeminiSession:
    def __init__(self):
        self.p = pyaudio.PyAudio()

    def openAudioStream(self):
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=1024
        )
        logging.info("Output Audio stream opened")

    def closeAudioStream(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        logging.info("Output Audio stream closed")

    async def openConn(self, db: keyManager.KeyManager):
        key_id = db.getKeyId()
        while True:
            try:
                start = time.perf_counter()
                self.client = genai.Client(api_key=os.getenv(key_id))
                self.session_context = self.client.aio.live.connect(model=model, config=config)
                self.session = await self.session_context.__aenter__()
                end = time.perf_counter()
                break
            except websockets.exceptions.ConnectionClosedError as e:
                logging.error(e)
                asyncio.create_task(db.insertKeyLog(key_id, False, e.code))
                key_id = db.getKeyId()

        logging.info(f"Gemini websocket connection opened in: {end - start}s")
        return key_id

    async def closeConn(self):
        await self.session_context.__aexit__(None, None, None)
        logging.info("Gemini connection terminated")

    async def send_prompt(self, prompt):
        await self.session.send_client_content(
            turns={
                "role": "user",
                "parts": [{"text": prompt}]
            },
            turn_complete=True
        )
        logging.info(f"Prompt sent: {prompt}")

        total_bytes = 0

        async for response in self.session.receive():
            if response.data:
                chunk_size = len(response.data)
                total_bytes += chunk_size
                self.stream.write(response.data)

        return total_bytes

    async def go_away(self):
        async for res in self.session.receive():
            if res.go_away:
                print("Server requested disconnect")

# async def main():
#     streamer = GeminiSession()
#     streamer.openAudioStream()
#     await streamer.openConn("API_KEY0")
#     await streamer.send_prompt("What is difference between goroutines and coroutines?")
#     await streamer.closeConn()
#     streamer.closeAudioStream()

# if __name__ == "__main__":
#     asyncio.run(main())