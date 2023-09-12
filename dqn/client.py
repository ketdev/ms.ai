import socket
import time
import threading
import numpy as np
from struct import pack
from pynput import keyboard

from capture.screen_capture import get_window_bounds, capture_screen, scale_image_to, grayscale_image, to_numpy_rgb, to_numpy_grayscale, compress_image
from logic.metrics import get_metric_percentages
from logic.config import CAPTURE_TARGET_FPS, SERVER_IP, PORT, \
    TARGET_WINDOW_NAME, FRAME_WIDTH, FRAME_HEIGHT, FRAMES_PER_STEP, \
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
## Helper functions
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

def send_data(sock, metrics, frame):
    data_block = b''
    data_block += pack('f', metrics["HP"])
    data_block += pack('f', metrics["MP"])
    data_block += pack('f', metrics["EXP"])
    data_block += frame.tobytes()

    bytes_sent = 0
    while bytes_sent < len(data_block):
        sent = sock.send(data_block[bytes_sent:])
        if sent == 0:
            raise Exception("Socket connection broken")
        bytes_sent += sent
    return bytes_sent
  
def recv_action(sock):
    action = sock.recv(1)
    if action == b'':
        raise Exception("Socket connection broken")
    return action

## ==================================================================
## Main Processes
## ==================================================================

def send_loop(sock, x, y, w, h):
    frame_count = 0
    fps_start_time = time.time()
    while not stop_capture:
        timestamp = time.time()

        # Capture frame and save to buffer
        frame, metrics = next(capture_frame(x, y, w, h))

        # Send frames to server
        send_data(sock, metrics, frame)

        # Update frames per second
        frame_count += 1
        if time.time() - fps_start_time >= 1:
            print(f"Send FPS: {frame_count}")
            frame_count = 0
            fps_start_time = time.time()

        # Calculate remaining delay to maintain target FPS
        elapsed_time = time.time() - timestamp
        sleep_time = FRAME_DELAY - elapsed_time
        if sleep_time > 0:
            time.sleep(sleep_time)

def recv_loop(sock):
    frame_step = 0
    while not stop_capture:
        # Recv action after enough frames
        frame_step += 1
        if frame_step >= FRAMES_PER_STEP:
            frame_step = 0
            action = recv_action(sock)
            print(f"Action: {action}")

def main():
    
    # Initialize the socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.connect((SERVER_IP, PORT))

    # Get bounds for target window
    title, bounds = get_window_bounds(TARGET_WINDOW_NAME).popitem()
    x = bounds["position"]["x"] + WINDOW_MARGIN_LEFT
    y = bounds["position"]["y"] + WINDOW_MARGIN_TOP
    w = bounds["size"]["width"] - (WINDOW_MARGIN_LEFT + WINDOW_MARGIN_RIGHT)
    h = bounds["size"]["height"] - (WINDOW_MARGIN_TOP + WINDOW_MARGIN_BOTTOM)
    print(f"Found: {title} (x:{x} y:{y} w:{w} h:{h})")

    # Start the keyboard listener thread
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.start()

    # Start send and recv threads
    send_thread = threading.Thread(target=send_loop, args=(s, x, y, w, h))
    recv_thread = threading.Thread(target=recv_loop, args=(s,))
    
    send_thread.start()
    recv_thread.start()
    
    # Wait for threads to finish
    send_thread.join()
    recv_thread.join()
    keyboard_thread.join()

    # Close the connection
    s.close()


if __name__ == '__main__':
    main()