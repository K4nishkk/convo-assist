from google import genai
from google.genai import types
import pyaudio
import asyncio
import websockets

# PyAudio configuration
RATE = 24000
CHANNELS = 1
FORMAT = pyaudio.paInt16

model = "gemini-2.5-flash-preview-native-audio-dialog"
config = types.LiveConnectConfig(response_modalities=[types.Modality.AUDIO])

async def live(message, api_key):
    client = genai.Client(api_key=api_key)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            await session.send_client_content(turns={"role": "user", "parts": [{"text": message}]}, turn_complete=True)

            async for response in session.receive():
                if response.data:
                    stream.write(response.data)

        print("stream complete")

    except websockets.exceptions.ConnectionClosedError as e:
        # print(f"Code: {e.code}")
        # print(f"Reason: {e.reason}")
        raise e

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

# if __name__ == "__main__":
#     asyncio.run(live("How does apache kafka work?", "API_KEY"))