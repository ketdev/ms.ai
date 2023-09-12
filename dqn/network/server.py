import socket
import time
import threading
import numpy as np
from pynput import keyboard

from logic.config import PORT, FRAME_WIDTH, FRAME_HEIGHT


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

def recv_frame(sock):
    chunks = []
    bytes_recd = 0
    while bytes_recd < FRAME_SIZE:
        chunk = sock.recv(min(FRAME_SIZE - bytes_recd, BUFFER_SIZE))
        if chunk == b'':
            raise Exception("Socket connection broken")
        chunks.append(chunk)
        bytes_recd += len(chunk)
    return b''.join(chunks)

def recv_metrics(sock):
    metrics_data = sock.recv(METRICS_SIZE)
    if len(metrics_data) < METRICS_SIZE:
        raise Exception("Socket connection broken")
    metrics_array = np.frombuffer(metrics_data, dtype=np.float32)
    return {
        "HP": metrics_array[0],
        "MP": metrics_array[1],
        "EXP": metrics_array[2]
    }

def action(frame, metrics):
    # For the sake of simplicity, this function will just
    # return a dummy action byte. Replace with your own logic!
    dummy_action = b'0'
    return dummy_action

def main():
    # Start the keyboard listener thread
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.start()

    # Initialize the socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PORT))
    s.listen(1)

    client_socket, client_address = s.accept()
    print(f"Connection from {client_address}")

    # Capture frames and send them to the server
    while not stop_capture:
        frame = recv_frame(client_socket)
        metrics = recv_metrics(client_socket)

        frame_array = np.frombuffer(frame_data, dtype=np.uint8).reshape(FRAME_HEIGHT, FRAME_WIDTH)
        print(f"Metrics: {metrics}")

        action = action(frame_array, metrics)

        client_socket.send(action)

    # Close the connection
    s.close()

    # Join the keyboard listener thread
    keyboard_thread.join()


if __name__ == '__main__':
    main()