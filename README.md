# waveHome

waveHome is a Python IoT smart home gesture-control prototype. It uses an ESP32-CAM video stream, MediaPipe hand landmarks, and OpenCV overlays to let a user control a virtual smart lamp with hand gestures.

The project is aimed at making smart home control more accessible for deaf, hard-of-hearing, and speech-disabled people by offering a non-verbal control path that can later be connected to Google Home compatible devices.

## Features

- Live camera display from an ESP32-CAM MJPEG stream.
- MediaPipe hand landmark detection.
- Hand bones, bounding boxes, gesture labels, and finger-state overlays.
- 800x600-friendly OpenCV UI with compact status panels.
- Virtual lamp state shown on screen.
- Scratch-like scenario dashboard for editing gesture workflows as blocks.
- Future-ready smart-home action layer with a Google Home bridge adapter.
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
  - `fastapi`
  - `uvicorn`
  - `pydantic`

Install dependencies with your preferred Python environment, for example:

```bash
python3 -m pip install opencv-python mediapipe numpy requests fastapi uvicorn pydantic
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



## Rule-based workflow mode

waveHome includes a rule-based workflow engine.

Instead of hardcoding every gesture directly in Python, gestures are converted into workflow events. Rules from `wavehome/rules/default_rules.json` decide what action should happen.

### Safety model

The default rules use command mode to reduce accidental triggers:

```text
both open palms held for 1s -> command mode active
command mode active -> normal rules are allowed
command mode expired -> protected rules are ignored
```

For testing with one hand, there is also a fallback wake rule:

```text
open palm held for 1.8s -> command mode active
```

Dangerous/global actions can also require confirmation. For example:

```text
both fists held -> pending confirmation
two thumbs up -> execute all off
thumb down -> cancel
```


### Dashboard

Run the dashboard API and editor:

```bash
uvicorn wavehome.web.server:app --reload --host 127.0.0.1 --port 8080
```

Open:
```text
http://127.0.0.1:8080/
```

Useful API endpoints:

```text
GET /api/health
GET /api/capabilities
GET /api/gestures
GET /api/rules
PUT /api/rules
```

Current trigger types
```text
sequence
hold
armed_hold
motion
value_control
```

Current action types
```text
workflow.enter_command_mode
workflow.exit_command_mode
workflow.cancel
virtual_lamp.toggle
virtual_lamp.turn_on
virtual_lamp.turn_off
virtual_lamp.toggle_party
virtual_lamp.brightness_step
virtual_lamp.brightness_set
virtual_lamp.color_set
```

Example flow
```text
1. Hold both open palms for 1 second.
2. Command mode becomes active.
3. Swipe up/down to change brightness.
4. Hold peace sign and rotate it to change color.
5. Hold both fists, then show two thumbs up, to turn everything off.
```

## Block workflow dashboard

The dashboard can now be used as a visual rule editor instead of only editing raw JSON.

Run it with:

```bash
uvicorn wavehome.web.server:app --reload --host 127.0.0.1 --port 8080
```

Open:

```text
http://127.0.0.1:8080/
```

Useful endpoints:

```text
GET  /api/health
GET  /api/capabilities
GET  /api/gestures
GET  /api/presets
GET  /api/rules
POST /api/rules/validate
PUT  /api/rules
POST /api/rules/reset
```

The rule editor is backed by JSON, but the dashboard exposes blocks for:

- trigger type: sequence, hold, repeat hold, armed hold, motion, value control;
- action type: lamp toggle, on/off, brightness, color, party mode, workflow control;
- future smart-home actions: power, brightness, color, scene activation;
- safety: cooldown, command mode, confirmation gesture, confirmation timeout.

Recommended safe workflow:

```text
1. Wake: hold both open palms.
2. Command mode becomes active.
3. Execute normal gesture rules.
4. Confirm dangerous actions with two thumbs up.
5. Cancel with thumb down.
```

See `docs/workflow_gesture_design.md` for the gesture vocabulary and false-trigger protection model.

## Future Google Home Bridge

The Python app now has a provider boundary for smart-home actions:

```text
smart_home.set_power
smart_home.set_brightness
smart_home.set_color
smart_home.activate_scene
```

By default these actions are inert unless a bridge is configured. Set these environment variables when a Google Home bridge service is ready:

```bash
export WAVEHOME_GOOGLE_HOME_ENABLED=true
export WAVEHOME_GOOGLE_HOME_BRIDGE_URL=http://127.0.0.1:9000
export WAVEHOME_GOOGLE_HOME_ACCESS_TOKEN=replace-with-token
```

The adapter posts normalized commands to `/commands`; that bridge can later own OAuth, permissions, and platform-specific Google Home API calls.
