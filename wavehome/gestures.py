import math

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
    middle_mcp = landmarks[9]

    palm_size = max(distance_2d(wrist, middle_mcp), 0.001)
    tip_from_wrist = distance_2d(wrist, thumb_tip)
    ip_from_wrist = distance_2d(wrist, thumb_ip)
    tip_from_thumb_mcp = distance_2d(thumb_mcp, thumb_tip)
    ip_from_thumb_mcp = distance_2d(thumb_mcp, thumb_ip)
    tip_from_index_mcp = distance_2d(thumb_tip, index_mcp)
    ip_from_index_mcp = distance_2d(thumb_ip, index_mcp)
    tip_from_middle_mcp = distance_2d(thumb_tip, middle_mcp)

    mcp_angle = angle_2d(thumb_cmc, thumb_mcp, thumb_ip)
    ip_angle = angle_2d(thumb_mcp, thumb_ip, thumb_tip)

    extends_from_wrist = tip_from_wrist > ip_from_wrist + palm_size * 0.03
    extends_from_thumb_base = tip_from_thumb_mcp > ip_from_thumb_mcp + palm_size * 0.06
    separated_from_palm = (
        tip_from_index_mcp > palm_size * 0.30
        and tip_from_middle_mcp > palm_size * 0.38
        and tip_from_index_mcp > ip_from_index_mcp + palm_size * 0.02
    )
    straight_enough = mcp_angle > 95 and ip_angle > 130

    return (
        extends_from_wrist
        and extends_from_thumb_base
        and separated_from_palm
        and straight_enough
    )


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


def is_peace_gesture(fingers):
    return (
        fingers["index"]
        and fingers["middle"]
        and not fingers["ring"]
        and not fingers["pinky"]
    )


def is_horns_gesture(fingers):
    return (
        fingers["index"]
        and not fingers["middle"]
        and not fingers["ring"]
        and fingers["pinky"]
    )


def peace_rotation_degrees(landmarks):
    base_x = (landmarks[5].x + landmarks[9].x) / 2.0
    base_y = (landmarks[5].y + landmarks[9].y) / 2.0
    tip_x = (landmarks[8].x + landmarks[12].x) / 2.0
    tip_y = (landmarks[8].y + landmarks[12].y) / 2.0

    dx = tip_x - base_x
    dy = tip_y - base_y

    if dx == 0 and dy == 0:
        return 0.0

    return math.degrees(math.atan2(dx, -dy))


def thumb_direction(landmarks, fingers):
    if fingers["index"] or fingers["middle"] or fingers["ring"] or fingers["pinky"]:
        return None

    wrist = landmarks[0]
    thumb_mcp = landmarks[2]
    thumb_ip = landmarks[3]
    thumb_tip = landmarks[4]
    index_mcp = landmarks[5]
    middle_mcp = landmarks[9]

    palm_size = max(distance_2d(wrist, middle_mcp), 0.001)
    vertical_delta = thumb_tip.y - thumb_mcp.y
    horizontal_delta = thumb_tip.x - thumb_mcp.x

    if abs(vertical_delta) < palm_size * 0.30:
        return None

    thumb_extended = (
        distance_2d(wrist, thumb_tip) > distance_2d(wrist, thumb_ip) + palm_size * 0.12
        and angle_2d(thumb_mcp, thumb_ip, thumb_tip) > 145
    )
    separated_from_palm = (
        distance_2d(thumb_tip, index_mcp) > palm_size * 0.35
        and distance_2d(thumb_tip, index_mcp) > distance_2d(thumb_ip, index_mcp) + palm_size * 0.05
    )
    vertical_enough = abs(vertical_delta) > abs(horizontal_delta) * 1.05

    if not (thumb_extended and separated_from_palm and vertical_enough):
        return None

    tip_past_ip = abs(thumb_tip.y - thumb_ip.y) > palm_size * 0.08

    if not tip_past_ip:
        return None

    if vertical_delta < 0 and thumb_tip.y < thumb_ip.y:
        return "UP"

    if vertical_delta > 0 and thumb_tip.y > thumb_ip.y:
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

    if is_horns_gesture(fingers):
        return "Horns"

    if fingers["index"] and not fingers["middle"] and not fingers["ring"] and not fingers["pinky"]:
        return "Pointing / 1 finger"

    if is_peace_gesture(fingers):
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

    if is_peace_gesture(fingers):
        return "PEACE"

    if is_horns_gesture(fingers):
        return "HORNS"

    return None


def command_label(command_key, fallback="none"):
    if command_key is None:
        return fallback

    return COMMAND_LABELS[command_key]
