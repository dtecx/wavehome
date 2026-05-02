import requests

from .config import MODEL_PATH, MODEL_URL


def ensure_model_exists():
    if MODEL_PATH.exists():
        return

    print("Downloading MediaPipe hand model...")
    print(f"Saving to: {MODEL_PATH}")

    response = requests.get(MODEL_URL, timeout=30)
    response.raise_for_status()

    MODEL_PATH.write_bytes(response.content)

    print("Model downloaded.")
