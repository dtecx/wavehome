import cv2
import numpy as np
import math


LAMP_WIN_WIDTH = 300
LAMP_WIN_HEIGHT = 600
BG_COLOR = (30, 30, 30)


def draw_lamp_window(controller, now):
    """Draw a standalone lamp visualization window."""
    frame = np.full((LAMP_WIN_HEIGHT, LAMP_WIN_WIDTH, 3), BG_COLOR, dtype=np.uint8)

    cx = LAMP_WIN_WIDTH // 2
    lamp_rgb = controller.current_lamp_rgb()
    lamp_bgr = (lamp_rgb[2], lamp_rgb[1], lamp_rgb[0])

    # --- Title ---
    title = "waveHome Lamp"
    t_size, _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    cv2.putText(frame, title, (cx - t_size[0] // 2, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    # --- Glow effect when lamp is on ---
    bulb_cy = 200
    bulb_radius = 70

    if controller.lamp_on:
        glow_color = lamp_rgb
        for r in range(140, bulb_radius, -4):
            alpha = 0.04 * (1.0 - (r - bulb_radius) / (140 - bulb_radius))
            overlay = frame.copy()
            cv2.circle(overlay, (cx, bulb_cy), r,
                       (glow_color[2], glow_color[1], glow_color[0]), -1)
            cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)

    # --- Bulb shape ---
    cv2.circle(frame, (cx, bulb_cy), bulb_radius, lamp_bgr, -1)
    cv2.circle(frame, (cx, bulb_cy), bulb_radius + 2, (180, 180, 180), 2)

    # --- Bulb base (screw part) ---
    base_top = bulb_cy + bulb_radius - 10
    base_w = 36
    for i in range(4):
        y = base_top + i * 12
        shade = 160 - i * 20
        cv2.rectangle(frame, (cx - base_w // 2, y), (cx + base_w // 2, y + 10),
                      (shade, shade, shade), -1)
        cv2.rectangle(frame, (cx - base_w // 2, y), (cx + base_w // 2, y + 10),
                      (100, 100, 100), 1)

    # --- Filament lines when ON ---
    if controller.lamp_on and not controller.party_mode:
        fil_color = (0, 200, 255)
        pts = []
        for i in range(20):
            x = cx - 15 + int(15 * math.sin(i * 0.8))
            y = bulb_cy - 30 + i * 3
            pts.append((x, y))
        for i in range(len(pts) - 1):
            cv2.line(frame, pts[i], pts[i + 1], fil_color, 2, cv2.LINE_AA)

    # --- Party mode sparkles ---
    if controller.party_mode and controller.party_visible:
        rng = np.random.RandomState(int(now * 5) % 10000)
        for _ in range(12):
            angle = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(bulb_radius + 10, bulb_radius + 50)
            sx = int(cx + dist * math.cos(angle))
            sy = int(bulb_cy + dist * math.sin(angle))
            spark_color = (rng.randint(100, 256), rng.randint(100, 256), rng.randint(100, 256))
            size = rng.randint(2, 6)
            cv2.circle(frame, (sx, sy), size, spark_color, -1)

    # --- Status text ---
    y_text = 360

    if controller.party_mode:
        status = "PARTY MODE"
        status_color = (0, 0, 255)
    elif controller.lamp_on:
        status = "LAMP ON"
        status_color = (0, 220, 0)
    else:
        status = "LAMP OFF"
        status_color = (0, 0, 180)

    t_size, _ = cv2.getTextSize(status, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    cv2.putText(frame, status, (cx - t_size[0] // 2, y_text),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color, 2, cv2.LINE_AA)

    # --- Brightness bar ---
    bar_y = y_text + 30
    bar_x = 40
    bar_w = LAMP_WIN_WIDTH - 80
    bar_h = 20

    cv2.putText(frame, f"Brightness: {controller.brightness}%",
                (bar_x, bar_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

    bar_y += 10
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                  (70, 70, 70), -1)
    fill_w = int(bar_w * controller.brightness / 100)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h),
                  (0, 190, 255), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                  (180, 180, 180), 1)

    # --- Color swatch ---
    swatch_y = bar_y + bar_h + 20
    cv2.putText(frame, "Color:", (bar_x, swatch_y + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

    swatch_x = bar_x + 70
    swatch_size = 30
    cv2.rectangle(frame, (swatch_x, swatch_y - 15),
                  (swatch_x + swatch_size, swatch_y - 15 + swatch_size),
                  lamp_bgr, -1)
    cv2.rectangle(frame, (swatch_x, swatch_y - 15),
                  (swatch_x + swatch_size, swatch_y - 15 + swatch_size),
                  (180, 180, 180), 1)

    rgb_text = f"({lamp_rgb[0]}, {lamp_rgb[1]}, {lamp_rgb[2]})"
    cv2.putText(frame, rgb_text, (swatch_x + swatch_size + 10, swatch_y + 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1, cv2.LINE_AA)

    # --- Message ---
    msg = controller.active_message(now)
    if msg:
        max_chars = 35
        lines = [msg[i:i + max_chars] for i in range(0, len(msg), max_chars)]
        msg_y = swatch_y + 40
        for line in lines:
            cv2.putText(frame, line, (20, msg_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 255), 1, cv2.LINE_AA)
            msg_y += 20

    # --- Bottom hint ---
    hint = "Gesture control active"
    t_size, _ = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
    cv2.putText(frame, hint, (cx - t_size[0] // 2, LAMP_WIN_HEIGHT - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)

    return frame