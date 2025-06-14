import asyncio
from config import setup_args
from speechSession import setup_microphone, conversation_loop
from whisperTranscriber import load_whisper_model
from keyManager import KeyManager
from geminiClient import GeminiSession
from constants import *

async def main():
    args = setup_args()
    
    model = load_whisper_model(args.model, args.non_english)
    recognizer, mic = setup_microphone(args.energy_threshold)

    db = KeyManager(DB_PATH, YAML_FILE_PATH)
    await db.preset()

    streamer = GeminiSession()
    streamer.openAudioStream()
    key_id = await streamer.openConn(db)

    await conversation_loop(
        model,
        recognizer,
        mic,
        args.phrase_timeout,
        args.record_timeout,
        db,
        streamer,
        key_id
    )

if __name__ == "__main__":

    asyncio.run(main())
