from geminiClient import GeminiSession
import logging
import time
import asyncio
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)

async def main():
    streamer = GeminiSession("API_KEY3")
    start = time.perf_counter()
    try:
        await streamer.start()
    except websockets.ConnectionClosedError as e:
        print(e.code)
    await streamer.stop()
    end = time.perf_counter()
    logging.info(f"WS connection opened in {(end - start):.2f}s")
    print(streamer.session)

if __name__ == "__main__":
    asyncio.run(main())