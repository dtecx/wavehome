import time
import threading
import math
from pathlib import Path

import requests
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision


# -----------------------------
# ESP32-CAM stream address
# -----------------------------
CAMERA_URL = "http://esp32cam.local/stream"
# CAMERA_URL = "http://1.1.1.1/stream"

MAX_HANDS = 2
APP_NAME = "waveHome"

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")

LAMP_TOGGLE_SEQUENCE = ("OPEN_PALM", "FIST", "OPEN_PALM", "FIST")
SEQUENCE_TIMEOUT_SECONDS = 15.0
GESTURE_HOLD_SECONDS = 0.30
TOGGLE_COOLDOWN_SECONDS = 1.50
COMMAND_LABELS = {
    "OPEN_PALM": "5 fingers up",
    "FIST": "fist",
}

latest_jpg = None
latest_id = 0
stop_program = False

lock = threading.Lock()


# -----------------------------
# MediaPipe hand connections
# -----------------------------
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),                    # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),                    # index
    (5, 9), (9, 10), (10, 11), (11, 12),               # middle
    (9, 13), (13, 14), (14, 15), (15, 16),             # ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),   # pinky
]


# -----------------------------
# Model downloader
# -----------------------------
def ensure_model_exists():
    if MODEL_PATH.exists():
        return

    print("Downloading MediaPipe hand model...")
    print(f"Saving to: {MODEL_PATH}")

    response = requests.get(MODEL_URL, timeout=30)
    response.raise_for_status()

    MODEL_PATH.write_bytes(response.content)

    print("Model downloaded.")


# -----------------------------
# ESP32-CAM stream reader
# -----------------------------
def camera_reader():
    global latest_jpg, latest_id, stop_program

    reconnect_delay = 1.0

    while not stop_program:
        print(f"Connecting to ESP32-CAM stream: {CAMERA_URL}")

        response = None

        try:
            response = requests.get(
                CAMERA_URL,
                stream=True,
                timeout=(3, 5),
                headers={
                    "Connection": "close",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )

            response.raise_for_status()
            print("Connected.")

            buffer = bytearray()

            while not stop_program:
                chunk = response.raw.read(8192, decode_content=False)

                if not chunk:
                    raise RuntimeError("Stream ended")

                buffer.extend(chunk)

                last_complete_jpg = None

                while True:
                    start = buffer.find(b"\xff\xd8")
                    end = buffer.find(b"\xff\xd9", start + 2)

                    if start == -1 or end == -1:
                        break

                    last_complete_jpg = bytes(buffer[start:end + 2])
                    del buffer[:end + 2]

                # Store only newest frame
                if last_complete_jpg is not None:
                    with lock:
                        latest_jpg = last_complete_jpg
                        latest_id += 1

                # Protection against broken stream buffer
                if len(buffer) > 300_000:
                    buffer.clear()

        except Exception as e:
            print(f"Stream error: {e}")
            print(f"Reconnecting in {reconnect_delay} second...")

            try:
                if response is not None:
                    response.close()
            except Exception:
                pass

            time.sleep(reconnect_delay)


# -----------------------------
# Geometry helpers
# -----------------------------
def distance_2d(a, b):
    dx = a.x - b.x
    dy = a.y - b.y
    return math.sqrt(dx * dx + dy * dy)


def angle_2d(a, b, c):
    """
    Returns angle ABC in degrees.
    """

    ab_x = a.x - b.x
    ab_y = a.y - b.y

    cb_x = c.x - b.x
    cb_y = c.y - b.y

    dot = ab_x * cb_x + ab_y * cb_y

    ab_len = math.sqrt(ab_x * ab_x + ab_y * ab_y)
    cb_len = math.sqrt(cb_x * cb_x + cb_y * cb_y)

    if ab_len == 0 or cb_len == 0:
        return 0

    value = dot / (ab_len * cb_len)
    value = max(-1.0, min(1.0, value))

    return math.degrees(math.acos(value))


def landmark_to_pixel(landmark, width, height):
    x = int(landmark.x * width)
    y = int(landmark.y * height)

    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))

    return x, y


# -----------------------------
# Gesture logic
# -----------------------------
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
    thumb_ip = landmarks[3]
    thumb_tip = landmarks[4]
    index_mcp = landmarks[5]

    tip_distance = distance_2d(wrist, thumb_tip)
    ip_distance = distance_2d(wrist, thumb_ip)

    thumb_angle = angle_2d(thumb_cmc, thumb_ip, thumb_tip)

    far_from_wrist = tip_distance > ip_distance * 1.15
    away_from_index = distance_2d(thumb_tip, index_mcp) > distance_2d(thumb_ip, index_mcp) * 1.20
    straight_enough = thumb_angle > 130

    return far_from_wrist and away_from_index and straight_enough


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


def classify_gesture(finger_count, fingers):
    thumb = fingers["thumb"]
    index = fingers["index"]
    middle = fingers["middle"]
    ring = fingers["ring"]
    pinky = fingers["pinky"]

    if finger_count == 0:
        return "Fist"

    if finger_count == 5:
        return "Open palm"

    if index and not middle and not ring and not pinky:
        return "Pointing / 1 finger"

    if index and middle and not ring and not pinky:
        return "Peace / 2 fingers"

    if thumb and index and middle and not ring and not pinky:
        return "3 fingers"

    if not thumb and index and middle and ring and pinky:
        return "4 fingers"

    return f"{finger_count} fingers"


def command_key_from_finger_count(finger_count):
    if finger_count == 5:
        return "OPEN_PALM"

    if finger_count == 0:
        return "FIST"

    return None


class VirtualLampController:
    def __init__(self):
        self.lamp_on = False
        self.brightness = 60
        self.sequence = LAMP_TOGGLE_SEQUENCE
        self.step_index = 0
        self.started_at = None
        self.last_step_at = None
        self.candidate_key = None
        self.candidate_since = 0.0
        self.last_accepted_key = None
        self.cooldown_until = 0.0
        self.message = "Ready: show 5 fingers up"
        self.message_until = 0.0

    def reset_sequence(self):
        self.step_index = 0
        self.started_at = None
        self.last_step_at = None

    def active_message(self, now):
        if self.message_until and now < self.message_until:
            return self.message

        if self.step_index == 0:
            return "Ready: 5 fingers up"

        remaining = self.remaining_seconds(now)
        next_key = self.sequence[self.step_index]

        return (
            f"Step {self.step_index}/{len(self.sequence)}; "
            f"next: {COMMAND_LABELS[next_key]}; {remaining:.0f}s left"
        )

    def remaining_seconds(self, now):
        if self.started_at is None:
            return SEQUENCE_TIMEOUT_SECONDS

        return max(0.0, SEQUENCE_TIMEOUT_SECONDS - (now - self.started_at))

    def update(self, command_key, now):
        if (
            self.step_index > 0
            and self.started_at is not None
            and now - self.started_at > SEQUENCE_TIMEOUT_SECONDS
        ):
            self.reset_sequence()
            self.message = "Sequence timed out"
            self.message_until = now + 2.0

        if command_key is None:
            self.candidate_key = None
            self.candidate_since = 0.0
            self.last_accepted_key = None
            return None

        if command_key != self.candidate_key:
            self.candidate_key = command_key
            self.candidate_since = now
            return None

        if now - self.candidate_since < GESTURE_HOLD_SECONDS:
            return None

        if command_key == self.last_accepted_key or now < self.cooldown_until:
            return None

        expected_key = self.sequence[self.step_index]

        if command_key == expected_key:
            return self.accept_sequence_step(command_key, now)

        self.reset_sequence()
        self.last_accepted_key = command_key

        if command_key == self.sequence[0]:
            self.started_at = now
            self.step_index = 1
            self.last_step_at = now
            self.message = "Sequence restarted"
        else:
            self.message = f"Start with {COMMAND_LABELS[self.sequence[0]]}"

        self.message_until = now + 2.0
        return "reset"

    def accept_sequence_step(self, command_key, now):
        if self.step_index == 0:
            self.started_at = now

        self.step_index += 1
        self.last_step_at = now
        self.last_accepted_key = command_key

        if self.step_index == len(self.sequence):
            self.lamp_on = not self.lamp_on
            self.cooldown_until = now + TOGGLE_COOLDOWN_SECONDS
            self.reset_sequence()
            self.message = f"Virtual lamp toggled {'ON' if self.lamp_on else 'OFF'}"
            self.message_until = now + 3.0
            return "toggle"

        next_key = self.sequence[self.step_index]
        self.message = f"Good; now {COMMAND_LABELS[next_key]}"
        self.message_until = now + 1.2
        return "step"


# -----------------------------
# Drawing helpers
# -----------------------------
def draw_plain_text(frame, text, position, font_scale=0.55, color=(255, 255, 255), thickness=1):
    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def draw_text_with_background(frame, text, position, font_scale=0.7):
    x, y = position

    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 2

    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    text_w, text_h = text_size

    cv2.rectangle(
        frame,
        (x - 6, y - text_h - 8),
        (x + text_w + 6, y + 8),
        (0, 0, 0),
        -1,
    )

    cv2.putText(
        frame,
        text,
        (x, y),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )


def draw_hand_landmarks(frame, landmarks, hand_index):
    height, width = frame.shape[:2]

    if hand_index == 0:
        point_color = (0, 255, 0)
        tip_color = (0, 255, 255)
        line_color = (255, 255, 255)
    else:
        point_color = (255, 0, 255)
        tip_color = (255, 255, 0)
        line_color = (255, 255, 255)

    for start_id, end_id in HAND_CONNECTIONS:
        start = landmark_to_pixel(landmarks[start_id], width, height)
        end = landmark_to_pixel(landmarks[end_id], width, height)

        cv2.line(frame, start, end, line_color, 2)

    for idx, landmark in enumerate(landmarks):
        x, y = landmark_to_pixel(landmark, width, height)

        if idx in [4, 8, 12, 16, 20]:
            color = tip_color
            radius = 6
        else:
            color = point_color
            radius = 4

        cv2.circle(frame, (x, y), radius, color, -1)
        cv2.circle(frame, (x, y), radius + 1, (0, 0, 0), 1)


def draw_bounding_box(frame, landmarks):
    height, width = frame.shape[:2]

    xs = [int(lm.x * width) for lm in landmarks]
    ys = [int(lm.y * height) for lm in landmarks]

    padding = 20

    x1 = max(0, min(xs) - padding)
    y1 = max(0, min(ys) - padding)
    x2 = min(width - 1, max(xs) + padding)
    y2 = min(height - 1, max(ys) + padding)

    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)

    return x1, y1, x2, y2


def draw_finger_states_for_hand(frame, fingers, hand_index):
    _, width = frame.shape[:2]

    if hand_index == 0:
        x = 10
        y = 165
    else:
        x = width - 185
        y = 165

    draw_text_with_background(
        frame,
        f"Hand {hand_index + 1}",
        (x, y),
        0.55,
    )

    y += 30

    for name in ["thumb", "index", "middle", "ring", "pinky"]:
        state = "UP" if fingers[name] else "DOWN"

        draw_text_with_background(
            frame,
            f"{name}: {state}",
            (x, y),
            0.45,
        )

        y += 25


def draw_sequence_steps(frame, controller, origin):
    x, y = origin
    labels = ["5", "F", "5", "F"]
    box_size = 27
    gap = 8

    for idx, label in enumerate(labels):
        box_x = x + idx * (box_size + gap)

        if idx < controller.step_index:
            fill_color = (42, 178, 94)
            text_color = (255, 255, 255)
        elif idx == controller.step_index:
            fill_color = (0, 190, 255)
            text_color = (0, 0, 0)
        else:
            fill_color = (70, 70, 70)
            text_color = (230, 230, 230)

        cv2.rectangle(
            frame,
            (box_x, y),
            (box_x + box_size, y + box_size),
            fill_color,
            -1,
        )

        cv2.rectangle(
            frame,
            (box_x, y),
            (box_x + box_size, y + box_size),
            (230, 230, 230),
            1,
        )

        text_size, _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            2,
        )
        text_x = box_x + (box_size - text_size[0]) // 2
        text_y = y + (box_size + text_size[1]) // 2

        draw_plain_text(
            frame,
            label,
            (text_x, text_y),
            0.52,
            text_color,
            2,
        )


def draw_wavehome_overlay(
    frame,
    hands_status,
    fps,
    dropped,
    controller,
    primary_command_label,
    now,
):
    _, frame_width = frame.shape[:2]
    overlay_height = 145

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame_width, overlay_height), (12, 12, 12), -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
    cv2.line(frame, (0, overlay_height), (frame_width, overlay_height), (80, 80, 80), 1)

    draw_plain_text(frame, APP_NAME, (10, 31), 0.78, (255, 255, 255), 2)
    draw_plain_text(
        frame,
        "gesture smart home control",
        (142, 31),
        0.45,
        (190, 220, 230),
        1,
    )

    draw_plain_text(
        frame,
        f"Hands: {hands_status}",
        (10, 62),
        0.55,
        (255, 255, 255),
        2,
    )

    draw_plain_text(
        frame,
        f"FPS: {fps:.1f}   Dropped: {dropped}   Max hands: {MAX_HANDS}",
        (10, 91),
        0.55,
        (255, 255, 255),
        2,
    )

    draw_plain_text(
        frame,
        f"Primary command: {primary_command_label}   Q=quit",
        (10, 122),
        0.52,
        (220, 220, 220),
        1,
    )

    panel_x = max(350, frame_width - 285)
    lamp_color = (0, 220, 255) if controller.lamp_on else (95, 95, 95)
    lamp_text = "ON" if controller.lamp_on else "OFF"

    cv2.circle(frame, (panel_x + 22, 29), 15, lamp_color, -1)
    cv2.circle(frame, (panel_x + 22, 29), 18, (245, 245, 245), 1)
    cv2.rectangle(
        frame,
        (panel_x + 13, 46),
        (panel_x + 31, 52),
        (180, 180, 180),
        -1,
    )

    draw_plain_text(
        frame,
        f"Virtual lamp: {lamp_text}",
        (panel_x + 50, 33),
        0.58,
        (255, 255, 255),
        2,
    )

    draw_plain_text(
        frame,
        f"Brightness: {controller.brightness}%",
        (panel_x + 50, 61),
        0.48,
        (210, 210, 210),
        1,
    )

    draw_plain_text(
        frame,
        "Toggle: 5 up > fist > 5 up > fist",
        (panel_x, 91),
        0.42,
        (235, 235, 235),
        1,
    )

    draw_sequence_steps(frame, controller, (panel_x, 103))

    draw_plain_text(
        frame,
        controller.active_message(now),
        (panel_x, 139),
        0.40,
        (0, 220, 255),
        1,
    )


# -----------------------------
# Display / detection loop
# -----------------------------
def display_loop():
    global stop_program

    ensure_model_exists()

    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = vision.HandLandmarker
    HandLandmarkerOptions = vision.HandLandmarkerOptions
    VisionRunningMode = vision.RunningMode

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=VisionRunningMode.VIDEO,
        num_hands=MAX_HANDS,
        min_hand_detection_confidence=0.40,
        min_hand_presence_confidence=0.40,
        min_tracking_confidence=0.40,
    )

    landmarker = HandLandmarker.create_from_options(options)
    lamp_controller = VirtualLampController()

    last_seen_id = -1

    frames = 0
    dropped = 0
    fps = 0.0
    last_fps_time = time.time()

    last_timestamp_ms = 0

    while not stop_program:
        with lock:
            jpg = latest_jpg
            current_id = latest_id

        if jpg is None or current_id == last_seen_id:
            time.sleep(0.005)
            continue

        if last_seen_id != -1:
            skipped = current_id - last_seen_id - 1
            if skipped > 0:
                dropped += skipped

        last_seen_id = current_id

        image_array = np.frombuffer(jpg, dtype=np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if frame is None:
            print("Bad JPEG frame, skipping")
            continue

        # Resize for speed.
        frame = cv2.resize(frame, (640, 480))

        # Mirror view.
        frame = cv2.flip(frame, 1)

        frame_height, _ = frame.shape[:2]

        # MediaPipe expects RGB.
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame,
        )

        timestamp_ms = int(time.monotonic() * 1000)

        # Timestamp must always increase in VIDEO mode.
        if timestamp_ms <= last_timestamp_ms:
            timestamp_ms = last_timestamp_ms + 1

        last_timestamp_ms = timestamp_ms

        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        detected_hands_text = []
        controlling_command_key = None
        controlling_command_label = "none"

        if result.hand_landmarks:
            for hand_index, landmarks in enumerate(result.hand_landmarks):
                finger_count, fingers = count_fingers(landmarks)
                gesture = classify_gesture(finger_count, fingers)
                command_key = command_key_from_finger_count(finger_count)

                if controlling_command_key is None and command_key is not None:
                    controlling_command_key = command_key
                    controlling_command_label = COMMAND_LABELS[command_key]
                elif controlling_command_label == "none":
                    controlling_command_label = gesture

                handedness_text = f"Hand {hand_index + 1}"

                if result.handedness and hand_index < len(result.handedness):
                    handedness = result.handedness[hand_index][0]
                    handedness_text = f"{handedness.category_name} {handedness.score:.2f}"

                detected_hands_text.append(
                    f"H{hand_index + 1}: {gesture} ({finger_count})"
                )

                draw_hand_landmarks(frame, landmarks, hand_index)
                x1, y1, x2, y2 = draw_bounding_box(frame, landmarks)

                draw_text_with_background(
                    frame,
                    f"H{hand_index + 1}: {handedness_text}",
                    (x1, max(30, y1 - 10)),
                    0.55,
                )

                draw_text_with_background(
                    frame,
                    gesture,
                    (x1, min(frame_height - 10, y2 + 25)),
                    0.55,
                )

                draw_finger_states_for_hand(frame, fingers, hand_index)

        now = time.time()
        lamp_controller.update(controlling_command_key, now)

        frames += 1

        if now - last_fps_time >= 1.0:
            fps = frames / (now - last_fps_time)
            frames = 0
            last_fps_time = now

        if detected_hands_text:
            hands_status = " | ".join(detected_hands_text)
        else:
            hands_status = "No hand detected"

        draw_wavehome_overlay(
            frame,
            hands_status,
            fps,
            dropped,
            lamp_controller,
            controlling_command_label,
            now,
        )

        cv2.imshow(f"{APP_NAME} ESP32-CAM Gesture Control", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            stop_program = True
            break

    landmarker.close()
    cv2.destroyAllWindows()


def main():
    global stop_program

    reader_thread = threading.Thread(target=camera_reader, daemon=True)
    reader_thread.start()

    try:
        display_loop()
    except KeyboardInterrupt:
        stop_program = True

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
