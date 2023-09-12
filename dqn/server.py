import socket
import time
import threading
import numpy as np
from struct import unpack
from pynput import keyboard

from logic.config import PORT, FRAME_WIDTH, FRAME_HEIGHT, FRAMES_PER_STEP
from capture.screen_capture import decompress_image, to_numpy_grayscale


## ==================================================================
## Constants
## ==================================================================

FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT
BUFFER_SIZE = 4096
METRICS_SIZE = 3 * 4  # Three float32 values


## ==================================================================
## Global Variables
## ==================================================================

# Global stop flag
stop_capture = False

# Global frames queue
frames_queue = Queue()


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

def send_action(sock, action):
    sock.send(action)

def recv_data(sock):
    # first receive the metrics
    metrics_data = sock.recv(METRICS_SIZE)
    if len(metrics_data) < METRICS_SIZE:
        raise Exception("Socket connection broken")
    metrics_array = unpack("fff", metrics_data)
    metrics = {
        "HP": metrics_array[0],
        "MP": metrics_array[1],
        "EXP": metrics_array[2]
    }

    # then receive the frame
    chunks = []
    bytes_recd = 0
    while bytes_recd < FRAME_SIZE:
        chunk = sock.recv(min(FRAME_SIZE - bytes_recd, BUFFER_SIZE))
        if chunk == b'':
            raise Exception("Socket connection broken")
        chunks.append(chunk)
        bytes_recd += len(chunk)
    frame = b''.join(chunks)

    # convert back to numpy array
    frame = np.frombuffer(frame, dtype=np.uint8)
    # frame = to_numpy_grayscale(frame)

    return frame, metrics
    
def get_action():
    # For the sake of simplicity, this function will just
    # return a dummy action byte. Replace with your own logic!
    dummy_action = b'0'
    return dummy_action


def receive_frames_thread(client_socket):
    while not stop_capture:
        frame, metrics = recv_data(client_socket)
        frames_queue.put((frame, metrics))


def process_frames_thread(client_socket):
    frame_step = 0
    while not stop_capture:
        frame_step += 1
        frame, metrics = frames_queue.get()

        # Send frames to server if reached target number of frames
        if frame_step >= FRAMES_PER_STEP:
            action = get_action()
            send_action(client_socket, action)
            frame_step = 0

def main():
    # Initialize the socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PORT))
    s.listen(1)

    client_socket, client_address = s.accept()
    print(f"Connection from {client_address}")

    # Start the keyboard listener thread
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.start()

    # Start threads
    recv_thread = threading.Thread(target=receive_frames_thread, args=(client_socket,))
    process_thread = threading.Thread(target=process_frames_thread, args=(client_socket,))
    recv_thread.start()
    process_thread.start()

    # Wait for threads to finish
    recv_thread.join()
    process_thread.join()
    keyboard_thread.join()

    # Close the connection
    client_socket.close()
    s.close()



if __name__ == '__main__':
    main()