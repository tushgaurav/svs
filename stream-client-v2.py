# On your robot: optimized-stream-client.py
import cv2
import requests
import numpy as np
from threading import Thread
import time
import queue

CLOUD_SERVER = "http://ec2-52-66-214-154.ap-south-1.compute.amazonaws.com:5000"


class WebcamStreamer:
    def __init__(self, camera_id, endpoint, target_fps=30, quality=70,
                 resize_factor=1.0, buffer_size=2):
        self.camera = cv2.VideoCapture(camera_id)

        # Set camera properties for performance
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.camera.set(cv2.CAP_PROP_FPS, target_fps)

        self.endpoint = endpoint
        self.running = True
        self.quality = quality  # JPEG compression quality (0-100)
        self.resize_factor = resize_factor  # 1.0 means no resize, 0.5 means half size
        self.target_fps = target_fps
        self.frame_time = 1 / target_fps

        # Frame sending queue and thread
        self.send_queue = queue.Queue(maxsize=buffer_size)
        self.send_thread = Thread(target=self._send_frames, daemon=True)
        self.send_thread.start()

    def _send_frames(self):
        session = requests.Session()
        while self.running:
            try:
                frame_data = self.send_queue.get(timeout=1.0)
                session.post(f"{CLOUD_SERVER}/{self.endpoint}",
                             files={"frame": frame_data})
            except queue.Empty:
                continue
            except requests.RequestException as e:
                print(f"Error sending frame to {self.endpoint}: {e}")
                time.sleep(0.1)

    def stream(self):
        last_frame_time = time.time()

        while self.running:
            current_time = time.time()
            # Ensure we're maintaining target FPS
            if current_time - last_frame_time < self.frame_time:
                continue

            ret, frame = self.camera.read()
            if ret:
                # Resize if needed
                if self.resize_factor != 1.0:
                    new_size = (int(frame.shape[1] * self.resize_factor),
                                int(frame.shape[0] * self.resize_factor))
                    frame = cv2.resize(frame, new_size)

                # Encode frame with specified quality
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
                _, img_encoded = cv2.imencode('.jpg', frame, encode_param)

                # Try to add to queue, skip frame if queue is full
                try:
                    self.send_queue.put(img_encoded.tobytes(), block=False)
                except queue.Full:
                    pass

                last_frame_time = current_time

    def start(self):
        Thread(target=self.stream, daemon=True).start()

    def stop(self):
        self.running = False
        self.camera.release()

# Performance monitoring class


class PerformanceMonitor:
    def __init__(self, window_size=30):
        self.frame_times = []
        self.window_size = window_size
        self.last_time = time.time()

    def update(self):
        current_time = time.time()
        self.frame_times.append(current_time - self.last_time)
        self.last_time = current_time

        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)

    def get_fps(self):
        if not self.frame_times:
            return 0
        return len(self.frame_times) / sum(self.frame_times)


# Example usage with performance monitoring
if __name__ == "__main__":
    # Configuration options
    TARGET_FPS = 30       # Adjust based on your needs and capabilities
    QUALITY = 70          # Reduce for less bandwidth, increase for better quality
    RESIZE_FACTOR = 0.75  # Reduce for less bandwidth, increase for better quality
    BUFFER_SIZE = 2       # Increase for smoother streaming, decrease for lower latency

    monitor1 = PerformanceMonitor()
    monitor2 = PerformanceMonitor()

    streamer1 = WebcamStreamer(
        0, "upload1", TARGET_FPS, QUALITY, RESIZE_FACTOR, BUFFER_SIZE)
    streamer2 = WebcamStreamer(
        1, "upload2", TARGET_FPS, QUALITY, RESIZE_FACTOR, BUFFER_SIZE)

    streamer1.start()
    streamer2.start()

    try:
        while True:
            monitor1.update()
            monitor2.update()

            if time.time() % 5 < 0.1:  # Print every 5 seconds
                print(f"Camera 1 FPS: {monitor1.get_fps():.1f}")
                print(f"Camera 2 FPS: {monitor2.get_fps():.1f}")

            time.sleep(0.1)
    except KeyboardInterrupt:
        streamer1.stop()
        streamer2.stop()
