# waveHome

waveHome is a Python IoT smart home gesture-control prototype. It uses an ESP32-CAM video stream, MediaPipe hand landmarks, and OpenCV overlays to let a user control a virtual smart lamp with hand gestures.

The project is aimed at making smart home control more accessible for deaf, hard-of-hearing, and speech-disabled people by offering a non-verbal control path that can later be connected to Google Home compatible devices.

## Features

- Live camera display from an ESP32-CAM MJPEG stream.
- MediaPipe hand landmark detection.
- Hand bones, bounding boxes, gesture labels, and finger-state overlays.
- 800x600-friendly OpenCV UI with compact status panels.
- Virtual lamp state shown on screen.
- Gesture command support:
  - Toggle lamp: `5 fingers up -> fist -> 5 fingers up -> fist`
  - Increase brightness: `fist -> thumb up`, then hold
  - Decrease brightness: `fist -> thumb down`, then hold
  - Set color: `fist -> peace`, then rotate the peace sign
  - Party mode: `fist -> horns -> fist`
- Modular code layout under `wavehome/`.

## Project Layout

```text
.
├── waveHome.py
└── wavehome/
    ├── app.py
    ├── camera.py
    ├── config.py
    ├── controller.py
    ├── drawing.py
    ├── geometry.py
    ├── gestures.py
    └── model.py
```

## Requirements

- Python 3.10+
- ESP32-CAM streaming MJPEG video
- Python packages:
  - `opencv-python`
  - `mediapipe`
  - `numpy`
  - `requests`

Install dependencies with your preferred Python environment, for example:

```bash
python3 -m pip install opencv-python mediapipe numpy requests
```

## Configuration

Camera and gesture settings live in:

```text
wavehome/config.py
```

By default the app expects:

```python
CAMERA_URL = "http://esp32cam.local/stream"
```

Update that value if your ESP32-CAM uses a different host or path.

For laptop webcam testing, set:

```python
USE_LOCAL_CAMERA = True
LOCAL_CAMERA_INDEX = None
```

When `USE_LOCAL_CAMERA` is `True`, the app ignores `CAMERA_URL` and reads frames from the local OpenCV webcam instead. `LOCAL_CAMERA_INDEX = None` auto-scans camera indexes and skips cameras that only return black frames. Set it to an integer like `0` or `1` to force a specific camera.

## Running

```bash
python3 waveHome.py
```

Press `q` in the OpenCV window to quit.

On first run, the app downloads the MediaPipe hand landmarker model to `hand_landmarker.task` if it is not already present.

## Gesture Guide

### Toggle Lamp

Show this sequence within 15 seconds:

```text
5 fingers up -> fist -> 5 fingers up -> fist
```

### Brightness

First make a fist to arm brightness control. Then:

- Hold thumb up for 3 seconds to increase brightness by 10%.
- Hold thumb down for 3 seconds to decrease brightness by 10%.
- Continue holding to repeat every 3 seconds.

Brightness is clamped between 0% and 100%.

### Color

First make a fist to arm color control. Then hold a peace sign and rotate it.

- `-60` degrees maps to RGB `(0, 0, 0)`.
- `0` degrees maps to RGB `(128, 128, 128)`.
- `60` degrees maps to RGB `(255, 255, 255)`.

The angle is measured from a straight vertical peace sign.

### Party Mode

Use:

```text
fist -> horns -> fist
```

The same sequence toggles party mode on or off. Party mode turns the lamp on, cycles colors, and blinks the lamp.

## Roadmap

- Real smart home device adapter.
- Google Home or Home Assistant integration.
- Config file or environment-variable based setup.
- Gesture calibration and automated tests.
