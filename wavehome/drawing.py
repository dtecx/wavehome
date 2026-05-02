import cv2

from .config import APP_NAME, MAX_HANDS
from .geometry import landmark_to_pixel
from .gestures import HAND_CONNECTIONS


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
        "Toggle: 5 > F > 5 > F",
        (panel_x, 86),
        0.42,
        (235, 235, 235),
        1,
    )

    draw_plain_text(
        frame,
        "Dim: F > thumb up/down, hold 3s",
        (panel_x, 105),
        0.38,
        (235, 235, 235),
        1,
    )

    draw_sequence_steps(frame, controller, (panel_x, 113))

    draw_plain_text(
        frame,
        controller.active_message(now),
        (panel_x, 139),
        0.40,
        (0, 220, 255),
        1,
    )
