import whisper
import torch

def load_whisper_model(model_name, non_english=False):
    full_name = model_name + ("" if non_english else ".en")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)
    return whisper.load_model(full_name).to(device)
