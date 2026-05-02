GESTURE_CATALOG = {
    "OPEN_PALM": {
        "label": "5 fingers up",
        "kind": "static",
        "description": "All five fingers visible. Good for wake, pause, or cancel.",
    },
    "FIST": {
        "label": "fist",
        "kind": "static",
        "description": "Closed hand. Good for arming a command mode.",
    },
    "THUMB_UP": {
        "label": "thumb up",
        "kind": "static",
        "description": "Thumb pointing up. Good for confirm or increase.",
    },
    "THUMB_DOWN": {
        "label": "thumb down",
        "kind": "static",
        "description": "Thumb pointing down. Good for reject or decrease.",
    },
    "PEACE": {
        "label": "peace",
        "kind": "static",
        "description": "Index and middle fingers open. Good for mode selection or color control.",
    },
    "HORNS": {
        "label": "horns",
        "kind": "static",
        "description": "Index and pinky open. Good for party or special mode.",
    },
    "POINT": {
        "label": "point",
        "kind": "static",
        "description": "Index finger only. Good for selecting a device or direction.",
    },
    "THREE": {
        "label": "3 fingers",
        "kind": "static",
        "description": "Three-finger gesture. Good for scene shortcuts.",
    },
    "FOUR": {
        "label": "4 fingers",
        "kind": "static",
        "description": "Four-finger gesture. Good for room or group actions.",
    },
    "PINCH": {
        "label": "pinch",
        "kind": "static",
        "description": "Thumb and index close together. Good for precise controls.",
    },
    "BOTH_OPEN_PALMS": {
        "label": "both open palms",
        "kind": "two_hand",
        "description": "Both hands open. Good for wake or command mode.",
    },
    "BOTH_FISTS": {
        "label": "both fists",
        "kind": "two_hand",
        "description": "Both hands closed. Good for emergency stop or all-off.",
    },
    "TWO_THUMBS_UP": {
        "label": "two thumbs up",
        "kind": "two_hand",
        "description": "Both thumbs up. Good for high-confidence confirmation.",
    },
    "SWIPE_LEFT": {
        "label": "swipe left",
        "kind": "motion",
        "description": "Hand moves left quickly. Good for previous device or scene.",
    },
    "SWIPE_RIGHT": {
        "label": "swipe right",
        "kind": "motion",
        "description": "Hand moves right quickly. Good for next device or scene.",
    },
    "SWIPE_UP": {
        "label": "swipe up",
        "kind": "motion",
        "description": "Hand moves upward. Good for brightness, volume, or blinds up.",
    },
    "SWIPE_DOWN": {
        "label": "swipe down",
        "kind": "motion",
        "description": "Hand moves downward. Good for brightness, volume, or blinds down.",
    },
}


def gesture_label(gesture_key: str | None, fallback: str = "none") -> str:
    if gesture_key is None:
        return fallback
    gesture = GESTURE_CATALOG.get(gesture_key)
    if gesture is None:
        return gesture_key
    return gesture["label"]


def gesture_kind(gesture_key: str | None, fallback: str = "static") -> str:
    if gesture_key is None:
        return fallback
    gesture = GESTURE_CATALOG.get(gesture_key)
    if gesture is None:
        return fallback
    return gesture["kind"]
