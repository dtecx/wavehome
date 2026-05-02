import threading
import time

import cv2
import numpy as np
import requests

from .config import (
    CAMERA_URL,
    LOCAL_CAMERA_BLACK_MEAN_THRESHOLD,
    LOCAL_CAMERA_BLACK_STD_THRESHOLD,
    LOCAL_CAMERA_SCAN_LIMIT,
)


class Esp32CameraStream:
    def __init__(self, url=CAMERA_URL):
        self.url = url
        self.source_label = "ESP32-CAM"
        self.status_text = url
        self.latest_jpg = None
        self.latest_id = 0
        self.stop_requested = False
        self.lock = threading.Lock()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_requested = True

    def get_latest(self):
        with self.lock:
            return self.latest_jpg, self.latest_id

    def _store_frame(self, jpg):
        with self.lock:
            self.latest_jpg = jpg
            self.latest_id += 1

    def _reader(self):
        reconnect_delay = 1.0

        while not self.stop_requested:
            print(f"Connecting to ESP32-CAM stream: {self.url}")
            response = None

            try:
                response = requests.get(
                    self.url,
                    stream=True,
                    timeout=(3, 5),
                    headers={
                        "Connection": "close",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                    },
                )

                response.raise_for_status()
                print("Connected.")

                buffer = bytearray()

                while not self.stop_requested:
                    chunk = response.raw.read(8192, decode_content=False)

                    if not chunk:
                        raise RuntimeError("Stream ended")

                    buffer.extend(chunk)
                    last_complete_jpg = None

                    while True:
                        start = buffer.find(b"\xff\xd8")
                        end = buffer.find(b"\xff\xd9", start + 2)

                        if start == -1 or end == -1:
                            break

                        last_complete_jpg = bytes(buffer[start:end + 2])
                        del buffer[:end + 2]

                    if last_complete_jpg is not None:
                        self._store_frame(last_complete_jpg)

                    if len(buffer) > 300_000:
                        buffer.clear()

            except Exception as e:
                print(f"Stream error: {e}")
                print(f"Reconnecting in {reconnect_delay} second...")

                try:
                    if response is not None:
                        response.close()
                except Exception:
                    pass

                time.sleep(reconnect_delay)


class LocalCameraStream:
    def __init__(self, camera_index=0, width=800, height=600):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.source_label = "Local camera"
        self.status_text = "starting"
        self.latest_jpg = None
        self.latest_id = 0
        self.stop_requested = False
        self.lock = threading.Lock()
        self.thread = None
        self._black_warning_at = 0.0

    def start(self):
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_requested = True

    def get_latest(self):
        with self.lock:
            return self.latest_jpg, self.latest_id

    def _store_frame(self, jpg):
        with self.lock:
            self.latest_jpg = jpg
            self.latest_id += 1

    def _reader(self):
        capture, first_frame = self._open_best_capture()

        if capture is None:
            return

        try:
            if first_frame is not None:
                self._encode_and_store(first_frame)

            while not self.stop_requested:
                ok, frame = capture.read()

                if not ok or frame is None:
                    self.status_text = "frame read failed"
                    print("Local camera frame read failed.")
                    time.sleep(0.1)
                    continue

                self._warn_if_black(frame)
                self._encode_and_store(frame)

                time.sleep(0.001)

        finally:
            capture.release()

    def _open_best_capture(self):
        candidates = self._capture_candidates()
        first_opened = None

        for index, backend_name, backend_id in candidates:
            capture = self._open_capture(index, backend_id)

            if capture is None:
                continue

            frame, mean, std = self._read_warm_frame(capture)
            looks_black = self._looks_black(mean, std)

            print(
                f"Local camera candidate index={index} backend={backend_name} "
                f"mean={mean:.1f} std={std:.1f}"
            )

            if first_opened is None:
                first_opened = (capture, frame, index, backend_name, mean, std)
            elif looks_black:
                capture.release()

            if frame is not None and not looks_black:
                if first_opened and first_opened[0] is not capture:
                    first_opened[0].release()
                self._set_open_status(index, backend_name)
                return capture, frame

        if first_opened is not None:
            capture, frame, index, backend_name, mean, std = first_opened
            self._set_open_status(index, backend_name)
            self.status_text += " - frames look black"
            print(
                "Local camera opened, but frames look black. "
                "Try another LOCAL_CAMERA_INDEX or close apps using the camera."
            )
            return capture, frame

        self.status_text = "no local camera opened"
        print("Local camera could not be opened.")
        return None, None

    def _capture_candidates(self):
        if self.camera_index is None:
            indexes = range(LOCAL_CAMERA_SCAN_LIMIT)
        else:
            indexes = [self.camera_index]

        backends = []

        if hasattr(cv2, "CAP_AVFOUNDATION"):
            backends.append(("AVFoundation", cv2.CAP_AVFOUNDATION))

        backends.append(("Default", cv2.CAP_ANY))

        return [
            (index, backend_name, backend_id)
            for index in indexes
            for backend_name, backend_id in backends
        ]

    def _open_capture(self, index, backend_id):
        print(f"Opening local camera index {index}")

        if backend_id == cv2.CAP_ANY:
            capture = cv2.VideoCapture(index)
        else:
            capture = cv2.VideoCapture(index, backend_id)

        if not capture.isOpened():
            capture.release()
            return None

        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self.width:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        return capture

    def _read_warm_frame(self, capture):
        best_frame = None
        best_mean = 0.0
        best_std = 0.0

        for _ in range(30):
            ok, frame = capture.read()

            if not ok or frame is None:
                time.sleep(0.03)
                continue

            mean, std = self._frame_stats(frame)

            if best_frame is None or std > best_std or mean > best_mean:
                best_frame = frame
                best_mean = mean
                best_std = std

            if not self._looks_black(mean, std):
                return frame, mean, std

            time.sleep(0.03)

        return best_frame, best_mean, best_std

    def _frame_stats(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray)), float(np.std(gray))

    def _looks_black(self, mean, std):
        return (
            mean < LOCAL_CAMERA_BLACK_MEAN_THRESHOLD
            and std < LOCAL_CAMERA_BLACK_STD_THRESHOLD
        )

    def _warn_if_black(self, frame):
        mean, std = self._frame_stats(frame)

        if not self._looks_black(mean, std):
            return

        now = time.time()

        if now - self._black_warning_at < 3.0:
            return

        self._black_warning_at = now
        self.status_text = f"{self.status_text.split(' - ')[0]} - black frame"
        print(
            f"Local camera frame looks black: mean={mean:.1f}, std={std:.1f}. "
            "Try another LOCAL_CAMERA_INDEX if this persists."
        )

    def _encode_and_store(self, frame):
        encoded, jpg = cv2.imencode(".jpg", frame)

        if encoded:
            self._store_frame(jpg.tobytes())

    def _set_open_status(self, index, backend_name):
        self.source_label = f"Local cam {index}"
        self.status_text = f"{backend_name}"
