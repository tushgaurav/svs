# On your VM: cloud-server.py
from flask import Flask, Response, request
from flask_cors import CORS
import cv2
import numpy as np
import threading
import queue

app = Flask(__name__)
CORS(app)

# Queues to hold the latest frames
frame_queues = {
    "cam1": queue.Queue(maxsize=1),
    "cam2": queue.Queue(maxsize=1)
}


def get_latest_frame(queue_name):
    while True:
        try:
            frame = frame_queues[queue_name].get()
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print(f"Error in get_latest_frame: {e}")
            yield b''


@app.route('/upload1', methods=['POST'])
def upload1():
    if 'frame' not in request.files:
        return 'No frame in request', 400

    frame_data = request.files['frame'].read()
    nparr = np.frombuffer(frame_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame_queues["cam1"].full():
        frame_queues["cam1"].get()  # Remove old frame
    frame_queues["cam1"].put(frame)
    return 'OK'


@app.route('/upload2', methods=['POST'])
def upload2():
    if 'frame' not in request.files:
        return 'No frame in request', 400

    frame_data = request.files['frame'].read()
    nparr = np.frombuffer(frame_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame_queues["cam2"].full():
        frame_queues["cam2"].get()  # Remove old frame
    frame_queues["cam2"].put(frame)
    return 'OK'


@app.route('/stream1')
def stream1():
    return Response(get_latest_frame("cam1"),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/stream2')
def stream2():
    return Response(get_latest_frame("cam2"),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
