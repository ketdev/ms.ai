import socket
import time
import threading
import numpy as np
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

        # data = to_numpy_grayscale(frame)
        data = compress_image(frame)

        yield data, metrics

def make_data_block(frames, metrics_buffer):
    data_block = b''

    # concat frames into one long array followed by metrics
    for i in range(FRAMES_PER_STEP):
        # Write metrics
        metric = metrics_buffer[i]
        for name in ["HP", "MP", "EXP"]:
            value = metric[name]
            if value is None:
                value = 0
            value = value.to_bytes(4, byteorder='big')
            data_block += value

        # Write frame length and frame data
        frame = frames[i]
        frame = frame.flatten()
        frame = frame.tobytes()
        frame_len = len(frame)
        frame_len = frame_len.to_bytes(4, byteorder='big')
        data_block += frame_len
        data_block += frame

    return data_block

def send_data(sock, data_block):
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

def main():
    
    # Initialize the socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
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

    # Initialize the frame buffer
    frame_data, metrics = next(capture_frame()) # dummy frame for dimensions
    frames = np.zeros((frame_data.shape[0], frame_data.shape[1], FRAMES_PER_STEP), dtype=np.uint8)
    metrics_buffer = []

    # Keep track of frames per second
    frame_count = 0
    fps_start_time = time.time()
    fps = 0

    # Capture frames and send them to the server
    frame_step = 0
    while not stop_capture:
        timestamp = time.time()

        # Capture frame and save to buffer
        frame_step += 1
        frame, metrics = next(capture_frame(x, y, w, h))

        # Add frame to buffer
        frames = np.roll(frames, -1, axis=2)
        frames[:, :, -1] = frame

        # Add metrics to buffer
        metrics_buffer.append(metrics)
        if len(metrics_buffer) > FRAMES_PER_STEP:
            metrics_buffer.pop(0)

        # Send frames to server if reached target number of frames
        if frame_step >= FRAMES_PER_STEP:
            data_block = make_data_block(frames, metrics_buffer)
            send_data(s, data_block)
            frame_step = 0

            action = recv_action(s)
            print(f"Action: {action}")

        # Update frames per second
        frame_count += 1
        if time.time() - fps_start_time >= 1:
            fps = frame_count
            frame_count = 0
            fps_start_time = time.time()

        # Print FPS
        print(f"FPS: {fps}")

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