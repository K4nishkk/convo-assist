from configs.logger_config import setup_logger
setup_logger()

import asyncio
from configs.listener_config import setup_args
from core.speechSession import setup_microphone, conversation_loop
from utils.whisperTranscriber import load_whisper_model
from utils.keyManager import KeyManager
from core.geminiClient import GeminiSession
from utils.constants import *

import logging
logging.getLogger(__name__)

async def main():
    args = setup_args()
    
    model = load_whisper_model(args.model, args.non_english)
    recognizer, mic = setup_microphone(args.energy_threshold)

    db = KeyManager(DB_PATH, YAML_FILE_PATH)
    await db.preset()
    streamer = GeminiSession(db)

    try:
        streamer.open_audio_stream()
        key_id = await streamer.connect_to_session()

        await conversation_loop(model, recognizer, mic, args.phrase_timeout, args.record_timeout, db, streamer, key_id)
    except Exception as e:
        logging.error(e)    
    finally:
        await streamer.terminate_session()
        streamer.close_audio_stream()

if __name__ == "__main__":
    asyncio.run(main())