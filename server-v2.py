# On your VM: optimized-cloud-server.py
from flask import Flask, Response, request
from flask_cors import CORS
import cv2
import numpy as np
import threading
import queue
import time

app = Flask(__name__)
CORS(app)


class StreamManager:
    def __init__(self):
        self.frame_queues = {}
        self.fps_counters = {}
        self.lock = threading.Lock()

    def get_or_create_queue(self, camera_id):
        with self.lock:
            if camera_id not in self.frame_queues:
                self.frame_queues[camera_id] = queue.Queue(maxsize=1)
                self.fps_counters[camera_id] = {
                    'count': 0, 'last_time': time.time()}
            return self.frame_queues[camera_id]

    def update_fps(self, camera_id):
        with self.lock:
            counter = self.fps_counters[camera_id]
            counter['count'] += 1
            current_time = time.time()
            if current_time - counter['last_time'] >= 5.0:
                fps = counter['count'] / (current_time - counter['last_time'])
                print(f"Camera {camera_id} FPS: {fps:.1f}")
                counter['count'] = 0
                counter['last_time'] = current_time


stream_manager = StreamManager()


def get_latest_frame(camera_id):
    while True:
        try:
            frame = stream_manager.get_or_create_queue(
                camera_id).get(timeout=1.0)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except queue.Empty:
            yield b''


@app.route('/upload<camera_id>', methods=['POST'])
def upload_frame(camera_id):
    if 'frame' not in request.files:
        return 'No frame in request', 400

    frame_data = request.files['frame'].read()
    queue = stream_manager.get_or_create_queue(camera_id)

    if queue.full():
        queue.get()  # Remove old frame
    queue.put(frame_data)

    stream_manager.update_fps(camera_id)
    return 'OK'


@app.route('/stream<camera_id>')
def stream_frame(camera_id):
    return Response(get_latest_frame(camera_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
