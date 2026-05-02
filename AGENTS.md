# waveHome Agent Notes

## Project Purpose

waveHome is an IoT smart home gesture-control prototype for people who are deaf, hard of hearing, speech-disabled, or otherwise prefer non-verbal home control. The current app reads a camera stream, detects hand landmarks with MediaPipe, recognizes simple gestures, and maps those gestures to a virtual lamp state.

The target direction is to use the same gesture command layer to control real smart home devices, especially Google Home compatible lights and scenes.

## Current Behavior

- Shows the live camera frame.
- Draws detected hand landmarks, bones, bounding boxes, gesture labels, and finger states.
- Uses an 800x600-friendly overlay with compact top, bottom, and hand-state panels.
- Controls a virtual lamp:
  - Toggle ON/OFF: `5 fingers up -> fist -> 5 fingers up -> fist` within 15 seconds.
  - Brightness: `fist -> thumb up/down`, then hold thumb up or down. Every 3 seconds changes brightness by 10%.
  - Color: `fist -> peace`, then rotate the peace sign across a -60 to 60 degree range.
  - Party mode: `fist -> horns -> fist` toggles blinking color cycling.
- Keeps app logic split into small modules under `wavehome/`.

## Code Map

- `waveHome.py`: entry point.
- `wavehome/app.py`: main camera, detection, gesture, and display loop.
- `wavehome/camera.py`: ESP32-CAM stream reader and local webcam reader.
- `wavehome/config.py`: constants and tunable settings.
- `wavehome/controller.py`: virtual lamp state and command sequencing.
- `wavehome/drawing.py`: OpenCV UI overlays and hand drawing.
- `wavehome/geometry.py`: landmark geometry helpers.
- `wavehome/gestures.py`: finger counting and command gesture classification.
- `wavehome/model.py`: MediaPipe model download helper.

## How To Run

1. Install Python dependencies used by the app:
   - `opencv-python`
   - `mediapipe`
   - `numpy`
   - `requests`
2. Make sure `CAMERA_URL` in `wavehome/config.py` points to the ESP32-CAM stream, or set `USE_LOCAL_CAMERA = True` to use a laptop webcam. Use `LOCAL_CAMERA_INDEX = None` for auto-detect or an integer index to force one camera.
3. Run:

```bash
python3 waveHome.py
```

Press `q` in the OpenCV window to quit.

## Development Notes

- Keep gesture recognition separate from device control. `wavehome/controller.py` should stay device-agnostic where possible.
- Prefer adding future smart home providers behind a small adapter interface, for example `set_power(device_id, on)` and `set_brightness(device_id, percent)`.
- Keep UI drawing in `wavehome/drawing.py`; avoid mixing overlay layout into `wavehome/app.py`.
- Tune thresholds in one place where possible, preferably `wavehome/config.py`.
- Run `python3 -m compileall waveHome.py wavehome` after code changes.

## Next Steps

- Add a real Google Home or Home Assistant integration layer.
- Add simple config loading from environment variables or a local config file.
- Add automated unit tests for gesture sequencing and brightness stepping.
- Add calibration helpers for camera angle, left/right handedness, and gesture sensitivity.
- Add more accessible gestures:
  - Swipe left/right to choose a device.
  - Open palm hold to cancel/back.
  - Pinch and vertical movement for smooth brightness control.
