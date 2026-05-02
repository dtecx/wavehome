from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .gestures import (
    classify_gesture,
    command_key_from_hand,
    command_label,
    count_fingers,
    peace_rotation_degrees,
)


@dataclass
class HandInfo:
    landmarks: Any
    finger_count: int
    fingers: dict[str, bool]
    gesture_label: str
    command_key: str | None
    command_value: float | None
    handedness_text: str
    palm_center: tuple[float, float]


@dataclass
class GestureFrame:
    command_key: str | None
    command_label: str
    command_value: float | None
    hands_status: str
    primary_palm_center: tuple[float, float] | None
    hands: list[HandInfo]


def palm_center(landmarks) -> tuple[float, float]:
    palm_ids = [0, 5, 9, 13, 17]
    x = sum(landmarks[index].x for index in palm_ids) / len(palm_ids)
    y = sum(landmarks[index].y for index in palm_ids) / len(palm_ids)
    return x, y


def two_hand_command(keys: list[str | None]) -> str | None:
    visible_keys = [key for key in keys if key is not None]

    if len(visible_keys) < 2:
        return None

    first_two = visible_keys[:2]

    if first_two.count("OPEN_PALM") == 2:
        return "BOTH_OPEN_PALMS"

    if first_two.count("FIST") == 2:
        return "BOTH_FISTS"

    if first_two.count("THUMB_UP") == 2:
        return "TWO_THUMBS_UP"

    return None


def extract_gesture_frame(result) -> GestureFrame:
    hands: list[HandInfo] = []

    if not result.hand_landmarks:
        return GestureFrame(
            command_key=None,
            command_label="none",
            command_value=None,
            hands_status="No hand detected",
            primary_palm_center=None,
            hands=[],
        )

    for hand_index, landmarks in enumerate(result.hand_landmarks):
        finger_count, fingers = count_fingers(landmarks)
        gesture = classify_gesture(finger_count, fingers, landmarks)
        key = command_key_from_hand(finger_count, fingers, landmarks)
        value = peace_rotation_degrees(landmarks) if key == "PEACE" else None

        handedness_text = f"Hand {hand_index + 1}"
        if result.handedness and hand_index < len(result.handedness):
            handedness = result.handedness[hand_index][0]
            handedness_text = f"{handedness.category_name} {handedness.score:.2f}"

        hands.append(
            HandInfo(
                landmarks=landmarks,
                finger_count=finger_count,
                fingers=fingers,
                gesture_label=gesture,
                command_key=key,
                command_value=value,
                handedness_text=handedness_text,
                palm_center=palm_center(landmarks),
            )
        )

    combined_key = two_hand_command([hand.command_key for hand in hands])

    if combined_key is not None:
        command_key = combined_key
        value = None
    else:
        primary = next((hand for hand in hands if hand.command_key is not None), hands[0])
        command_key = primary.command_key
        value = primary.command_value

    label = command_label(command_key)
    status = " | ".join(
        f"H{index + 1}: {hand.gesture_label} ({hand.finger_count})"
        for index, hand in enumerate(hands)
    )

    primary_center = hands[0].palm_center if hands else None

    return GestureFrame(
        command_key=command_key,
        command_label=label,
        command_value=value,
        hands_status=status,
        primary_palm_center=primary_center,
        hands=hands,
    )
