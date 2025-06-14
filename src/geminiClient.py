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
from constants import *

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)

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
    def __init__(self, db: keyManager.KeyManager):
        self.p = pyaudio.PyAudio()
        self.response_queue = asyncio.Queue()
        self._recv_task = None
        self._stop_event = asyncio.Event()
        self.db = db

    def open_audio_stream(self):
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            output=True,
            frames_per_buffer=AUDIO_FRAMES_PER_BUFFER
        )
        logging.info("Output Audio stream opened")

    def close_audio_stream(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        logging.info("Output Audio stream closed")
        
    async def _receiver_loop(self):
        logging.info("Listening to incoming stream of responses")
        try:
            while True:
                async for message in self.session.receive():
                    await self.response_queue.put(message)

                    if message.go_away:
                        logging.info(f"Server requested disconnect in {message.go_away.time_left}s")
                        logging.info(message.go_away)
                        await self.terminate_session()
                        await self.connect_to_session()
                        break
                    
                # block ends everytime after turn_complete
        except Exception as e:
            logging.error(f"Receiver loop error: {e}")
        finally:
            logging.info("Response stream closed")

    async def start_receiver(self):
        asyncio.create_task(self._receiver_loop())

    async def connect_to_session(self):
        key_id = self.db.getKeyId()
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
                asyncio.create_task(self.db.insertKeyLog(key_id, False, e.code))
                key_id = self.db.getKeyId()

        await self.start_receiver()

        logging.info(f"Gemini websocket connection opened in: {end - start}s")
        return key_id

    async def terminate_session(self):
        await self.session_context.__aexit__(None, None, None)
        logging.info("Gemini connection terminated")

    async def send_prompt(self, prompt):
        await self.session.send_client_content(
            turns={"role": "user", "parts": [{"text": prompt}]},
            turn_complete=True
        )
        logging.info(f"Prompt (dispatched): {prompt}")

        total_bytes = 0

        while True:
            response = await self.response_queue.get()

            if response.data:
                chunk_size = len(response.data)
                total_bytes += chunk_size
                self.stream.write(response.data)

            if response.server_content and response.server_content.turn_complete:
                break

        return total_bytes

    async def go_away(self):
        async for res in self.session.receive():
            if res.go_away:
                logging.info("Server requested disconnect")
                logging.info(res.go_away.time_left)

# async def main():
#     streamer = GeminiSession()
#     streamer.openAudioStream()
#     await streamer.openConn("API_KEY0")
#     await streamer.send_prompt("What is difference between goroutines and coroutines?")
#     await streamer.closeConn()
#     streamer.closeAudioStream()

# if __name__ == "__main__":
#     asyncio.run(main())