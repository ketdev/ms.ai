import socket
import time
import threading
import numpy as np
from pynput import keyboard

from capture.screen_capture import get_window_bounds, capture_screen, scale_image_to, grayscale_image, to_numpy_rgb, to_numpy_grayscale
from logic.metrics import get_metric_percentages
from logic.config import CAPTURE_TARGET_FPS, SERVER_IP, PORT, \
    TARGET_WINDOW_NAME, FRAME_WIDTH, FRAME_HEIGHT, \
    WINDOW_MARGIN_BOTTOM, WINDOW_MARGIN_LEFT, WINDOW_MARGIN_RIGHT, WINDOW_MARGIN_TOP

## ==================================================================
## Constants
## ==================================================================

FRAME_DELAY = 1.0 / CAPTURE_TARGET_FPS
FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT


## ==================================================================
## Global Variables
## ==================================================================

# Global stop flag
stop_capture = False


## ==================================================================
## Keyboard Stop Condition (press ESC to stop)
## ==================================================================

def start_keyboard_listener():
    def on_key_press(key):
        global stop_capture
        if key == keyboard.Key.esc:
            stop_capture = True
            return False
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()


## ==================================================================
## Main Processes
## ==================================================================

def capture_frame(x, y, w, h):
    while True:
        screenshot = next(capture_screen(x, y, w, h))
        img_data = to_numpy_rgb(screenshot) # np array

        # Calculate metrics from screenshot
        metrics = get_metric_percentages(img_data)

        # Frame is scaled down grayscale image
        frame = scale_image_to(screenshot, FRAME_WIDTH, FRAME_HEIGHT)
        frame = grayscale_image(frame)
        data = to_numpy_grayscale(frame)

        yield data, metrics

def send_frame(sock, frame):
    bytes_sent = 0
    while bytes_sent < FRAME_SIZE:
        frame = np.ascontiguousarray(frame)
        sent = sock.send(frame[bytes_sent:])
        if sent == 0:
            raise Exception("Socket connection broken")
        bytes_sent += sent
    return bytes_sent

def send_metrics(sock, metrics):
    values = []
    for name in ["HP", "MP", "EXP"]:
        value = metrics[name]
        if value is None:
            value = 0
        values.append(value)
    values = np.array(values, dtype=np.float32)
    values = values.tobytes()
    bytes_sent = 0
    while bytes_sent < len(values):
        sent = sock.send(values[bytes_sent:])
        if sent == 0:
            raise Exception("Socket connection broken")
        bytes_sent += sent
    return bytes_sent
        
def recv_action(sock):
    action = sock.recv(1)
    if action == b'':
        raise Exception("Socket connection broken")
    return action

def main():
    
    # Initialize the socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, PORT))

    # Start the keyboard listener thread
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.start()

    # Get bounds for target window
    title, bounds = get_window_bounds(TARGET_WINDOW_NAME).popitem()
    x = bounds["position"]["x"] + WINDOW_MARGIN_LEFT
    y = bounds["position"]["y"] + WINDOW_MARGIN_TOP
    w = bounds["size"]["width"] - (WINDOW_MARGIN_LEFT + WINDOW_MARGIN_RIGHT)
    h = bounds["size"]["height"] - (WINDOW_MARGIN_TOP + WINDOW_MARGIN_BOTTOM)
    print(f"Found: {title} (x:{x} y:{y} w:{w} h:{h})")

    # Keep track of frames per second
    frame_count = 0
    fps_start_time = time.time()
    fps = 0

    # Capture frames and send them to the server
    while not stop_capture:
        timestamp = time.time()

        # Capture frame and send it to the server
        frame, metrics = next(capture_frame(x, y, w, h))
        send_frame(s, frame)
        send_metrics(s, metrics)
        action = recv_action(s)
        # print(f"Action: {action}")

        # Update frames per second
        frame_count += 1
        if time.time() - fps_start_time >= 1:
            fps = frame_count
            frame_count = 0
            fps_start_time = time.time()

        # Print FPS
        print(f"FPS: {fps}", end="\r")

        # # Calculate remaining delay to maintain target FPS
        # elapsed_time = time.time() - timestamp
        # sleep_time = FRAME_DELAY - elapsed_time
        # if sleep_time > 0:
        #     time.sleep(sleep_time)
    
    # Close the connection
    s.close()

    # Join the keyboard listener thread
    keyboard_thread.join()


if __name__ == '__main__':
    main()