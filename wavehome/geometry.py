import math


def distance_2d(a, b):
    dx = a.x - b.x
    dy = a.y - b.y
    return math.sqrt(dx * dx + dy * dy)


def angle_2d(a, b, c):
    """Returns angle ABC in degrees."""
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
