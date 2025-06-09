import asyncio
from config import setup_args
from speechSession import setup_microphone, conversation_loop
from whisperTranscriber import load_whisper_model

async def main():
    args = setup_args()
    
    model = load_whisper_model(args.model, args.non_english)
    recognizer, mic = setup_microphone(args.energy_threshold)

    await conversation_loop(model, recognizer, mic, args.phrase_timeout, args.record_timeout)

if __name__ == "__main__":
    asyncio.run(main())
