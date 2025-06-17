import pyaudio
from utils.constants import *

import logging
logging.Logger(__name__)

class AudioPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()

    def open_audio_stream(self):
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            output=True,
            frames_per_buffer=AUDIO_FRAMES_PER_BUFFER
        )
        logging.info("Output Audio stream opened")

        return self.stream

    def close_audio_stream(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        logging.info("Output Audio stream closed")