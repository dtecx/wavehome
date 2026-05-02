from pathlib import Path


APP_NAME = "waveHome"

# ESP32-CAM stream address.
CAMERA_URL = "http://esp32cam.local/stream"
# CAMERA_URL = "http://1.1.1.1/stream"

# Set this to True to use the laptop webcam instead of the ESP32-CAM stream.
USE_LOCAL_CAMERA = False
LOCAL_CAMERA_INDEX = 0
LOCAL_CAMERA_WIDTH = 800
LOCAL_CAMERA_HEIGHT = 600

MAX_HANDS = 2
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 600

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
MODEL_PATH = PROJECT_ROOT / "hand_landmarker.task"

LAMP_TOGGLE_SEQUENCE = ("OPEN_PALM", "FIST", "OPEN_PALM", "FIST")
SEQUENCE_TIMEOUT_SECONDS = 15.0
GESTURE_HOLD_SECONDS = 0.30
TOGGLE_COOLDOWN_SECONDS = 1.50

BRIGHTNESS_ARM_TIMEOUT_SECONDS = 8.0
BRIGHTNESS_HOLD_STEP_SECONDS = 3.0
BRIGHTNESS_STEP_PERCENT = 10
BRIGHTNESS_MIN_PERCENT = 0
BRIGHTNESS_MAX_PERCENT = 100

COMMAND_LABELS = {
    "OPEN_PALM": "5 fingers up",
    "FIST": "fist",
    "THUMB_UP": "thumb up",
    "THUMB_DOWN": "thumb down",
}
