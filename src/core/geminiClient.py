from google import genai
from google.genai import types
import time
import os
import pyaudio
import asyncio
import utils.keyManager as keyManager
import websockets
from typing import Optional
from utils.constants import *

from dotenv import load_dotenv
load_dotenv()

import logging
logger = logging.getLogger(__name__)

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
    _TERMINATION_SENTINEL = object()

    def __init__(self, db: keyManager.KeyManager, audio_stream: pyaudio.Stream):
        self.stream = audio_stream
        self.response_queue = asyncio.Queue()
        self._recv_task: Optional[asyncio.Task] = None
        self.db = db
        self._recv_loop_running = False
        self._reconnect_lock = asyncio.Lock()
        
    async def _receiver_loop(self):
        if self._recv_loop_running:
            logging.warning("Receiver loop already running, skipping.")
            return
        self._recv_loop_running = True
    
        logging.info("Listening to incoming stream of responses")
        try:
            while True:
                async for message in self.session.receive():
                    await self.response_queue.put(message)

                    if message.go_away:
                        logging.info(f"Server requested disconnect in {message.go_away.time_left}")
                        await self.terminate_session()
                        return
                    
                # block ends everytime after turn_complete
        except websockets.exceptions.ConnectionClosedError as e:
            logging.error(f"Receiver loop error: {e}")
            self.db.insertKeyLog(self.key_id, False, e.code, comments=f"During receive: {e.reason}")
            await self.response_queue.put(self._TERMINATION_SENTINEL)
            await self.terminate_session()
            return
        finally:
            self._recv_loop_running = False
            logging.info("Response stream closed")

    async def _start_receiver(self):
        async def wrapper():
            while True:
                async with self._reconnect_lock:
                    await self._receiver_loop()
                    logging.info("Reconnecting to Gemini server...")
                    await self.connect_to_session(same_key_id=True)

        if self._recv_task and not self._recv_task.done():
            logging.warning("Receiver already active, skipping start.")
            return

        self._recv_task = asyncio.create_task(wrapper())

    async def connect_to_session(self, same_key_id = False):
        if not same_key_id:
            self.key_id = self.db.getKeyId()
        else:
            logging.info(f"Reconnecting with same KEY_ID: {self.key_id}")
            
        while True:
            try:
                start = time.perf_counter()
                self.client = genai.Client(api_key=os.getenv(self.key_id))
                self.session_context = self.client.aio.live.connect(model=model, config=config)
                self.session = await self.session_context.__aenter__()
                end = time.perf_counter()
                break
            except websockets.exceptions.ConnectionClosedError as e:
                logging.error(e)
                self.db.insertKeyLog(self.key_id, False, e.code, comments=f"During connect: {e.reason}")
                self.key_id = self.db.getKeyId()

        if not self._recv_loop_running:
            await self._start_receiver()

        logging.info(f"Gemini websocket connection opened in: {(end - start):.2f}s")
        return self.key_id

    async def terminate_session(self):
        logging.info("Terminating Gemini session...")

        # Cancel receiver task
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                logging.info("Receiver task cancelled")

        self._recv_task = None
        self._recv_loop_running = False

        # Clean up context
        if self.session_context:
            try:
                await self.session_context.__aexit__(None, None, None)
            except Exception as e:
                logging.warning(f"Context exit error: {e}")
            self.session_context = None

        logging.info("Gemini connection terminated")

    async def _clear_response_queue(self):
        while not self.response_queue.empty():
            try:
                self.response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def send_prompt(self, prompt):
        await self._clear_response_queue()
        await self.session.send_client_content(
            turns={"role": "user", "parts": [{"text": prompt}]},
            turn_complete=True
        )
        logging.info(f"Prompt (dispatched): {prompt}")

        total_bytes = 0

        while True:
            response = await self.response_queue.get()

            # TODO currently slow
            if response is self._TERMINATION_SENTINEL:
                logging.warning("Receiver loop failed — terminating prompt handling.")
                break

            elif response.data:
                chunk_size = len(response.data)
                total_bytes += chunk_size
                self.stream.write(response.data)

            elif response.server_content and response.server_content.turn_complete:
                break

        return total_bytes, self.key_id