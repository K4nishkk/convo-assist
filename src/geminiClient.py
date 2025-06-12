from google import genai
from google.genai import types
import pyaudio
import asyncio
import websockets
import logging

import time
import os
from dotenv import load_dotenv

load_dotenv()
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)

# PyAudio configuration
RATE = 24000
CHANNELS = 1
FORMAT = pyaudio.paInt16

model = "gemini-2.5-flash-preview-native-audio-dialog"
config = types.LiveConnectConfig(response_modalities=[types.Modality.AUDIO])

class GeminiSession:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=os.getenv(api_key))
        self.p = pyaudio.PyAudio()
        logging.info("Gemini Session initialized")

    async def start(self):
        self.session_context = self.client.aio.live.connect(model=model, config=config)
        self.session = await self.session_context.__aenter__()

        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=1024
        )
        logging.info("Gemini Session started")

    async def stop(self):
        if self.session_context:
            await self.session_context.__aexit__(None, None, None)
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        
        logging.info("Gemini Session stopped")

    async def send_prompt(self, message):
        await self.session.send_client_content(
            turns={
                "role": "user",
                "parts": [{"text": message}]
            },
            turn_complete=True
        )
        logging.info(f"message sent: {message}, awaiting response")

        async for response in self.session.receive():
            if response.data:
                self.stream.write(response.data)

    async def go_away(self):
        async for res in self.session.receive():
            if res.go_away:
                print("Server requested disconnect")

async def main():
    streamer = GeminiSession("API_KEY6")
    await streamer.start()
    await streamer.send_prompt("What is pyaudio stream")
    await streamer.stop()

if __name__ == "__main__":
    asyncio.run(main())