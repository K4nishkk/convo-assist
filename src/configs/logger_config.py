import logging
from datetime import datetime
import os

def setup_logger():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = f"logs/log_{timestamp}.log"
    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ],
        force=True  # Ensures it overrides any prior config
    )