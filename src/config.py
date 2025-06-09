import argparse
from sys import platform

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--non_english", action='store_true')
    parser.add_argument("--energy_threshold", default=1000, type=int)
    parser.add_argument("--record_timeout", default=2, type=float)
    parser.add_argument("--phrase_timeout", default=3, type=float)
    if 'linux' in platform:
        parser.add_argument("--default_microphone", default='pulse', type=str)
    return parser.parse_args()
