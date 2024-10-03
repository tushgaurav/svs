import cv2
import requests
import numpy as np
from threading import Thread
import time

CLOUD_SERVER = "http://52.66.214.154:5000"  # Replace with your VM's IP


class WebcamStreamer:
    def __init__(self, camera_id, endpoint):
        self.camera = cv2.VideoCapture(camera_id)
        self.endpoint = endpoint
        self.running = True

    def stream(self):
        while self.running:
            ret, frame = self.camera.read()
            if ret:
                _, img_encoded = cv2.imencode('.jpg', frame)
                try:
                    requests.post(f"{CLOUD_SERVER}/{self.endpoint}",
                                  files={"frame": img_encoded.tobytes()})
                except requests.RequestException as e:
                    print(f"Error streaming to {self.endpoint}: {e}")
            time.sleep(0.1)  # Adjust based on desired frame rate

    def start(self):
        Thread(target=self.stream, daemon=True).start()

    def stop(self):
        self.running = False
        self.camera.release()


if __name__ == "__main__":
    streamer1 = WebcamStreamer(0, "upload1")
    streamer2 = WebcamStreamer(4, "upload2")

    streamer1.start()
    streamer2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        streamer1.stop()
        streamer2.stop()
