import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision

from .camera import Esp32CameraStream, LocalCameraStream
from .config import (
    APP_NAME,
    LOCAL_CAMERA_HEIGHT,
    LOCAL_CAMERA_INDEX,
    LOCAL_CAMERA_WIDTH,
    MAX_HANDS,
    MODEL_PATH,
    USE_LOCAL_CAMERA,
)
from .controller import VirtualLampController
from .drawing import (
    draw_bounding_box,
    draw_finger_states_for_hand,
    draw_hand_landmarks,
    draw_text_with_background,
    draw_wavehome_overlay,
)
from .gestures import classify_gesture, command_key_from_hand, command_label, count_fingers
from .model import ensure_model_exists


def create_hand_landmarker():
    base_options = mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH))

    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=MAX_HANDS,
        min_hand_detection_confidence=0.40,
        min_hand_presence_confidence=0.40,
        min_tracking_confidence=0.40,
    )

    return vision.HandLandmarker.create_from_options(options)


def display_loop(camera_stream):
    ensure_model_exists()

    landmarker = create_hand_landmarker()
    lamp_controller = VirtualLampController()

    last_seen_id = -1

    frames = 0
    dropped = 0
    fps = 0.0
    last_fps_time = time.time()

    last_timestamp_ms = 0

    try:
        while True:
            jpg, current_id = camera_stream.get_latest()

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

            frame = cv2.resize(frame, (640, 480))
            frame = cv2.flip(frame, 1)

            frame_height, _ = frame.shape[:2]

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            timestamp_ms = int(time.monotonic() * 1000)

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
                    gesture = classify_gesture(finger_count, fingers, landmarks)
                    command_key = command_key_from_hand(finger_count, fingers, landmarks)

                    if controlling_command_key is None and command_key is not None:
                        controlling_command_key = command_key
                        controlling_command_label = command_label(command_key)
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
                break

    finally:
        landmarker.close()
        cv2.destroyAllWindows()


def main():
    if USE_LOCAL_CAMERA:
        camera_stream = LocalCameraStream(
            LOCAL_CAMERA_INDEX,
            LOCAL_CAMERA_WIDTH,
            LOCAL_CAMERA_HEIGHT,
        )
    else:
        camera_stream = Esp32CameraStream()

    camera_stream.start()

    try:
        display_loop(camera_stream)
    except KeyboardInterrupt:
        pass
    finally:
        camera_stream.stop()
        cv2.destroyAllWindows()
