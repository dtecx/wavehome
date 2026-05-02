import threading
import time

import requests

from .config import CAMERA_URL


class Esp32CameraStream:
    def __init__(self, url=CAMERA_URL):
        self.url = url
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
