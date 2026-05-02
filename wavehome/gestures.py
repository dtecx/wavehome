from .config import COMMAND_LABELS
from .geometry import angle_2d, distance_2d


HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),                    # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),                    # index
    (5, 9), (9, 10), (10, 11), (11, 12),               # middle
    (9, 13), (13, 14), (14, 15), (15, 16),             # ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),   # pinky
]


def is_finger_open(landmarks, mcp_id, pip_id, dip_id, tip_id):
    wrist = landmarks[0]
    mcp = landmarks[mcp_id]
    pip = landmarks[pip_id]
    dip = landmarks[dip_id]
    tip = landmarks[tip_id]

    tip_distance = distance_2d(wrist, tip)
    pip_distance = distance_2d(wrist, pip)

    pip_angle = angle_2d(mcp, pip, dip)
    dip_angle = angle_2d(pip, dip, tip)

    far_from_wrist = tip_distance > pip_distance * 1.12
    straight_enough = pip_angle > 145 and dip_angle > 140

    return far_from_wrist and straight_enough


def is_thumb_open(landmarks):
    wrist = landmarks[0]
    thumb_cmc = landmarks[1]
    thumb_mcp = landmarks[2]
    thumb_ip = landmarks[3]
    thumb_tip = landmarks[4]
    index_mcp = landmarks[5]

    tip_distance = distance_2d(wrist, thumb_tip)
    ip_distance = distance_2d(wrist, thumb_ip)

    thumb_angle = angle_2d(thumb_cmc, thumb_ip, thumb_tip)

    far_from_wrist = tip_distance > ip_distance * 1.15
    away_from_index = distance_2d(thumb_tip, index_mcp) > distance_2d(thumb_ip, index_mcp) * 1.20
    straight_enough = thumb_angle > 130
    vertical_delta = thumb_tip.y - wrist.y
    vertical_thumb = (
        abs(vertical_delta) > 0.07
        and tip_distance > ip_distance * 1.08
        and angle_2d(thumb_mcp, thumb_ip, thumb_tip) > 120
    )

    return (far_from_wrist and away_from_index and straight_enough) or vertical_thumb


def count_fingers(landmarks):
    fingers = {
        "thumb": is_thumb_open(landmarks),
        "index": is_finger_open(landmarks, 5, 6, 7, 8),
        "middle": is_finger_open(landmarks, 9, 10, 11, 12),
        "ring": is_finger_open(landmarks, 13, 14, 15, 16),
        "pinky": is_finger_open(landmarks, 17, 18, 19, 20),
    }

    finger_count = sum(1 for value in fingers.values() if value)

    return finger_count, fingers


def thumb_direction(landmarks, fingers):
    if fingers["index"] or fingers["middle"] or fingers["ring"] or fingers["pinky"]:
        return None

    wrist = landmarks[0]
    thumb_mcp = landmarks[2]
    thumb_ip = landmarks[3]
    thumb_tip = landmarks[4]
    vertical_delta = thumb_tip.y - wrist.y

    if abs(vertical_delta) < 0.07:
        return None

    thumb_extended = (
        distance_2d(wrist, thumb_tip) > distance_2d(wrist, thumb_ip) * 1.08
        and angle_2d(thumb_mcp, thumb_ip, thumb_tip) > 120
    )

    if not thumb_extended:
        return None

    if vertical_delta < 0 and thumb_tip.y < thumb_ip.y - 0.02:
        return "UP"

    if vertical_delta > 0 and thumb_tip.y > thumb_ip.y + 0.02:
        return "DOWN"

    return None


def classify_gesture(finger_count, fingers, landmarks):
    direction = thumb_direction(landmarks, fingers)

    if direction == "UP":
        return "Thumb up"

    if direction == "DOWN":
        return "Thumb down"

    if finger_count == 0:
        return "Fist"

    if finger_count == 5:
        return "Open palm"

    if fingers["index"] and not fingers["middle"] and not fingers["ring"] and not fingers["pinky"]:
        return "Pointing / 1 finger"

    if fingers["index"] and fingers["middle"] and not fingers["ring"] and not fingers["pinky"]:
        return "Peace / 2 fingers"

    if fingers["thumb"] and fingers["index"] and fingers["middle"] and not fingers["ring"] and not fingers["pinky"]:
        return "3 fingers"

    if not fingers["thumb"] and fingers["index"] and fingers["middle"] and fingers["ring"] and fingers["pinky"]:
        return "4 fingers"

    return f"{finger_count} fingers"


def command_key_from_hand(finger_count, fingers, landmarks):
    direction = thumb_direction(landmarks, fingers)

    if direction == "UP":
        return "THUMB_UP"

    if direction == "DOWN":
        return "THUMB_DOWN"

    if finger_count == 5:
        return "OPEN_PALM"

    if finger_count == 0:
        return "FIST"

    return None


def command_label(command_key, fallback="none"):
    if command_key is None:
        return fallback

    return COMMAND_LABELS[command_key]
