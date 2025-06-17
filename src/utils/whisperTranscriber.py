from faster_whisper import WhisperModel
import torch
import logging

logger = logging.getLogger(__name__)

def load_whisper_model(model_name, non_english=False):
    model = model_name + ("" if non_english else ".en")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    
    logging.info(f"Model: {model} | Device: {device} | compute_type: {compute_type}")

    return WhisperModel(
        model,
        device=device,
        compute_type=compute_type
    )