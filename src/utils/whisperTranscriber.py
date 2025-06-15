import whisper
import torch
import logging

import logging
logger = logging.getLogger(__name__)

def load_whisper_model(model_name, non_english=False):
    full_name = model_name + ("" if non_english else ".en")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"Using device: {device}")
    return whisper.load_model(full_name).to(device)
