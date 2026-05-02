import cv2

from .config import APP_NAME, MAX_HANDS
from .geometry import landmark_to_pixel
from .gestures import HAND_CONNECTIONS


TOP_BAR_HEIGHT = 98
BOTTOM_BAR_HEIGHT = 88
PANEL_MARGIN = 12


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


def draw_translucent_rect(frame, top_left, bottom_right, color, alpha=0.72):
    overlay = frame.copy()
    cv2.rectangle(overlay, top_left, bottom_right, color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


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
    panel_w = 214
    panel_h = 70
    y = TOP_BAR_HEIGHT + PANEL_MARGIN

    if hand_index == 0:
        x = PANEL_MARGIN
    else:
        x = width - panel_w - PANEL_MARGIN

    draw_translucent_rect(frame, (x, y), (x + panel_w, y + panel_h), (18, 18, 18), 0.74)
    cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), (95, 95, 95), 1)

    draw_plain_text(frame, f"Hand {hand_index + 1}", (x + 12, y + 23), 0.52, (255, 255, 255), 2)

    labels = [("T", "thumb"), ("I", "index"), ("M", "middle"), ("R", "ring"), ("P", "pinky")]

    for idx, (label, name) in enumerate(labels):
        cx = x + 22 + idx * 38
        cy = y + 49
        is_up = fingers[name]
        fill_color = (45, 185, 96) if is_up else (72, 72, 72)
        text_color = (255, 255, 255) if is_up else (190, 190, 190)

        cv2.circle(frame, (cx, cy), 13, fill_color, -1)
        cv2.circle(frame, (cx, cy), 14, (220, 220, 220), 1)

        text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        draw_plain_text(
            frame,
            label,
            (cx - text_size[0] // 2, cy + text_size[1] // 2),
            0.42,
            text_color,
            1,
        )


def draw_sequence_steps(frame, controller, origin):
    x, y = origin
    labels = ["5", "F", "5", "F"]
    box_size = 30
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
    camera_source,
    camera_status,
):
    frame_height, frame_width = frame.shape[:2]
    bottom_y = frame_height - BOTTOM_BAR_HEIGHT

    draw_translucent_rect(frame, (0, 0), (frame_width, TOP_BAR_HEIGHT), (12, 12, 12), 0.82)
    draw_translucent_rect(frame, (0, bottom_y), (frame_width, frame_height), (12, 12, 12), 0.82)
    cv2.line(frame, (0, TOP_BAR_HEIGHT), (frame_width, TOP_BAR_HEIGHT), (70, 70, 70), 1)
    cv2.line(frame, (0, bottom_y), (frame_width, bottom_y), (70, 70, 70), 1)

    draw_plain_text(frame, APP_NAME, (16, 34), 0.88, (255, 255, 255), 2)
    draw_plain_text(
        frame,
        "gesture smart home control",
        (165, 34),
        0.45,
        (190, 220, 230),
        1,
    )

    draw_plain_text(
        frame,
        f"Hands: {hands_status}",
        (16, 65),
        0.55,
        (255, 255, 255),
        2,
    )

    draw_plain_text(
        frame,
        f"FPS: {fps:.1f}   Dropped: {dropped}   Max hands: {MAX_HANDS}   Q=quit",
        (16, 88),
        0.46,
        (210, 210, 210),
        1,
    )

    draw_plain_text(
        frame,
        f"Cmd: {primary_command_label}",
        (360, 34),
        0.46,
        (225, 225, 225),
        1,
    )

    draw_plain_text(
        frame,
        f"{camera_source}: {camera_status}",
        (360, 58),
        0.40,
        (190, 220, 230),
        1,
    )

    panel_x = frame_width - 252
    panel_y = 14
    panel_w = 236
    panel_h = 70
    lamp_rgb = controller.current_lamp_rgb()
    lamp_color = (lamp_rgb[2], lamp_rgb[1], lamp_rgb[0])
    lamp_text = "ON" if controller.lamp_on else "OFF"
    if controller.party_mode:
        lamp_text = "PARTY"

    draw_translucent_rect(
        frame,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + panel_h),
        (28, 28, 28),
        0.78,
    )
    cv2.rectangle(frame, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (90, 90, 90), 1)

    cv2.circle(frame, (panel_x + 28, panel_y + 28), 16, lamp_color, -1)
    cv2.circle(frame, (panel_x + 28, panel_y + 28), 19, (245, 245, 245), 1)
    cv2.rectangle(
        frame,
        (panel_x + 18, panel_y + 47),
        (panel_x + 38, panel_y + 53),
        (180, 180, 180),
        -1,
    )

    draw_plain_text(
        frame,
        f"Virtual lamp: {lamp_text}",
        (panel_x + 58, panel_y + 28),
        0.54,
        (255, 255, 255),
        2,
    )

    bar_x = panel_x + 58
    bar_y = panel_y + 44
    bar_w = 154
    bar_h = 10
    fill_w = int(bar_w * controller.brightness / 100)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (72, 72, 72), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (0, 190, 255), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (220, 220, 220), 1)

    draw_plain_text(
        frame,
        f"Brightness: {controller.brightness}%",
        (panel_x + 58, panel_y + 66),
        0.42,
        (210, 210, 210),
        1,
    )

    draw_plain_text(
        frame,
        f"RGB: {lamp_rgb}",
        (panel_x + 58, panel_y + 82),
        0.34,
        (210, 210, 210),
        1,
    )

    draw_plain_text(
        frame,
        "Toggle lamp",
        (16, bottom_y + 28),
        0.56,
        (255, 255, 255),
        2,
    )
    draw_plain_text(frame, "5 > fist > 5 > fist", (16, bottom_y + 55), 0.47, (218, 218, 218), 1)
    draw_sequence_steps(frame, controller, (285, bottom_y + 32))

    draw_plain_text(
        frame,
        "Color",
        (460, bottom_y + 28),
        0.56,
        (255, 255, 255),
        2,
    )
    draw_plain_text(
        frame,
        "fist > peace, rotate",
        (460, bottom_y + 55),
        0.47,
        (218, 218, 218),
        1,
    )

    draw_plain_text(
        frame,
        "Party: fist > horns > fist",
        (460, bottom_y + 78),
        0.38,
        (218, 218, 218),
        1,
    )

    draw_plain_text(
        frame,
        controller.active_message(now),
        (16, bottom_y + 78),
        0.42,
        (0, 220, 255),
        1,
    )
