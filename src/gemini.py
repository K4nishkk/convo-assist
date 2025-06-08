from google import genai
from google.genai import types
import pyaudio

# PyAudio configuration
RATE = 24000
CHANNELS = 1
FORMAT = pyaudio.paInt16

client = genai.Client(api_key="API_KEY")
model = "gemini-2.5-flash-preview-native-audio-dialog"
config = types.LiveConnectConfig(response_modalities=[types.Modality.AUDIO])

async def live(message):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            await session.send_client_content(turns={"role": "user", "parts": [{"text": message}]}, turn_complete=True)

            async for response in session.receive():
                if response.data:
                    stream.write(response.data)

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()