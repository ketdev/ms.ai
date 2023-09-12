import socket
import time
import threading
import numpy as np
from pynput import keyboard

from logic.config import PORT, FRAME_WIDTH, FRAME_HEIGHT, FRAMES_PER_STEP


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


def recv_data_block(sock):
    metrics_buffer = []
    frames = []
    for i in range(FRAMES_PER_STEP):
        # first receive the metrics
        metrics_data = sock.recv(METRICS_SIZE)
        if len(metrics_data) < METRICS_SIZE:
            raise Exception("Socket connection broken")
        metrics_array = np.frombuffer(metrics_data, dtype=np.float32)
        metrics_buffer.append({
            "HP": metrics_array[0],
            "MP": metrics_array[1],
            "EXP": metrics_array[2]
        })

        # then receive the frame length
        frame_size_data = sock.recv(4)
        if len(frame_size_data) < 4:
            raise Exception("Socket connection broken")
        frame_size = int.from_bytes(frame_size_data, byteorder='big')

        chunks = []
        bytes_recd = 0
        while bytes_recd < frame_size:
            chunk = sock.recv(min(frame_size - bytes_recd, BUFFER_SIZE))
            if chunk == b'':
                raise Exception("Socket connection broken")
            chunks.append(chunk)
            bytes_recd += len(chunk)
        frame = b''.join(chunks)

        frame_array = np.frombuffer(frame, dtype=np.uint8).reshape(FRAME_HEIGHT, FRAME_WIDTH)
        frames.append(frame_array)

    return frames, metrics_buffer
    
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
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PORT))
    s.listen(1)

    client_socket, client_address = s.accept()
    print(f"Connection from {client_address}")

    # Capture frames and send them to the server
    while not stop_capture:
        frames, metrics_buffer = recv_data_block(client_socket)

        action = action(frames, metrics_buffer)

        client_socket.send(action)

    # Close the connection
    s.close()

    # Join the keyboard listener thread
    keyboard_thread.join()


if __name__ == '__main__':
    main()