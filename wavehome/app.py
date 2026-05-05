import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision

from .actions.router import CompositeActionAdapter
from .actions.smart_home import SmartHomeActions
from .actions.virtual_lamp import VirtualLampActions
from .camera import Esp32CameraStream, LocalCameraStream
from .config import (
    APP_NAME,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    GESTURE_HOLD_SECONDS,
    LOCAL_CAMERA_HEIGHT,
    LOCAL_CAMERA_INDEX,
    LOCAL_CAMERA_WIDTH,
    MAX_HANDS,
    MODEL_PATH,
    USE_LOCAL_CAMERA,
    USE_WORKFLOW_ENGINE,
)
from .controller import VirtualLampController
from .drawing import (
    draw_bounding_box,
    draw_finger_states_for_hand,
    draw_hand_landmarks,
    draw_text_with_background,
    draw_wavehome_overlay,
)
from .events import GestureEvent
from .model import ensure_model_exists
from .lamp_window import draw_lamp_window
from .motion import MotionDetector
from .providers.google_home import GoogleHomeAdapter
from .recognition import extract_gesture_frame
from .workflow.engine import WorkflowEngine
from .workflow.loader import enabled_rules, load_rules
from .workflow.stability import StableGestureFilter


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

    workflow_engine = None
    stable_filter = None

    if USE_WORKFLOW_ENGINE:
        rules_config = load_rules()
        action_adapter = CompositeActionAdapter(
            [
                VirtualLampActions(lamp_controller),
                SmartHomeActions(GoogleHomeAdapter.from_env()),
            ]
        )
        workflow_engine = WorkflowEngine(enabled_rules(rules_config), action_adapter)
        stable_filter = StableGestureFilter(GESTURE_HOLD_SECONDS)

    motion_detector = MotionDetector()

    last_seen_id = -1
    frames = 0
    dropped = 0
    fps = 0.0
    last_fps_time = time.time()
    last_timestamp_ms = 0
    last_wait_frame_time = 0.0

    try:
        while True:
            jpg, current_id = camera_stream.get_latest()

            if jpg is None:
                now = time.time()

                if now - last_wait_frame_time >= 0.25:
                    wait_frame = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8)

                    draw_wavehome_overlay(
                        wait_frame,
                        "Waiting for camera frame",
                        fps,
                        dropped,
                        lamp_controller,
                        "none",
                        now,
                        camera_stream.source_label,
                        camera_stream.status_text,
                    )


                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break

                time.sleep(0.005)
                continue

            if current_id == last_seen_id:
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

            frame = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
            frame = cv2.flip(frame, 1)
            frame_height, _ = frame.shape[:2]

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            timestamp_ms = int(time.monotonic() * 1000)
            if timestamp_ms <= last_timestamp_ms:
                timestamp_ms = last_timestamp_ms + 1
            last_timestamp_ms = timestamp_ms

            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            gesture_frame = extract_gesture_frame(result)

            for hand_index, hand in enumerate(gesture_frame.hands):
                draw_hand_landmarks(frame, hand.landmarks, hand_index)
                x1, y1, x2, y2 = draw_bounding_box(frame, hand.landmarks)

                draw_text_with_background(
                    frame,
                    f"H{hand_index + 1}: {hand.handedness_text}",
                    (x1, max(118, y1 - 10)),
                    0.55,
                )

                draw_text_with_background(
                    frame,
                    hand.gesture_label,
                    (x1, min(frame_height - 106, y2 + 25)),
                    0.55,
                )

                draw_finger_states_for_hand(frame, hand.fingers, hand_index)

            now = time.time()

            motion_key = motion_detector.update(gesture_frame.primary_palm_center, now)
            event_key = motion_key or gesture_frame.command_key
            event_label = gesture_frame.command_label
            event_value = gesture_frame.command_value

            if motion_key is not None:
                event_label = motion_key
                event_value = None

            if USE_WORKFLOW_ENGINE and workflow_engine is not None and stable_filter is not None:
                if motion_key is not None:
                    event = GestureEvent(
                        key=motion_key,
                        kind="motion",
                        confidence=1.0,
                        stable_ms=0,
                        value=None,
                        hand_count=len(gesture_frame.hands),
                        timestamp=now,
                        label=motion_key,
                    )
                else:
                    event = stable_filter.update_event(
                        event_key,
                        now,
                        event_value,
                        hand_count=len(gesture_frame.hands),
                    )

                workflow_engine.update_event(event, now)

                if workflow_engine.message:
                    lamp_controller.message = workflow_engine.message
                    lamp_controller.message_until = now + 2.0

                lamp_controller._update_party_frame(now)
            else:
                lamp_controller.update(
                    event_key,
                    now,
                    event_value,
                )

            frames += 1
            if now - last_fps_time >= 1.0:
                fps = frames / (now - last_fps_time)
                frames = 0
                last_fps_time = now

            draw_wavehome_overlay(
                frame,
                gesture_frame.hands_status,
                fps,
                dropped,
                lamp_controller,
                event_label,
                now,
                camera_stream.source_label,
                camera_stream.status_text,
            )

            cv2.imshow(f"{APP_NAME} {camera_stream.source_label} Gesture Control", frame)

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
