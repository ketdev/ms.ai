import socket
import time
import threading
import numpy as np
from struct import unpack
from pynput import keyboard
from queue import Queue

from logic.config import PORT, FRAME_WIDTH, FRAME_HEIGHT, FRAMES_PER_STEP
from capture.screen_capture import decompress_image, to_numpy_grayscale


## ==================================================================
## Constants
## ==================================================================

FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT
BUFFER_SIZE = 4096
METRICS_SIZE = 3 * 4  # Three float32 values

PACKET_SIZE = 1288

METRICS_TYPE = 0
CHUNK_TYPE = 1

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
## Action Logic
## ==================================================================

def get_action():
    # For the sake of simplicity, this function will just
    # return a dummy action byte. Replace with your own logic!
    dummy_action = b'0'
    return dummy_action


## ==================================================================
## Main Processes
## ==================================================================

def send_action(sock, addr, action):
    sock.sendto(action, addr)

def recv_packet(sock):

    packet, addr = sock.recvfrom(PACKET_SIZE)
    if len(packet) < PACKET_SIZE:
        raise Exception("Incomplete packet received")

    # print(f"Received packet from {addr}")

    # Interpret packet type (first 4 bytes) as integer
    packet_type = packet[:4]
    packet_type = unpack("i", packet_type)[0]

    # If packet is a metrics packet, unpack the metrics
    if packet_type == METRICS_TYPE:
        metrics_data = packet[4:METRICS_SIZE+4]
        metrics_array = unpack("fff", metrics_data)
        metrics = {
            "HP": metrics_array[0],
            "MP": metrics_array[1],
            "EXP": metrics_array[2]
        }
        return METRICS_TYPE, metrics, addr
    
    # If packet is a frame chunk packet, unpack the frame chunk
    elif packet_type == CHUNK_TYPE:
        row = packet[4:8]
        row = unpack("i", row)[0]
        data = packet[12:]
        data = np.frombuffer(data, dtype=np.uint8)
        chunk = (row, data)
        return CHUNK_TYPE, chunk, addr

    
def receive_frames_thread(sock):
    while not stop_capture:
        ptype, data, addr = recv_packet(sock)
        frames_queue.put((ptype, data, addr))

def process_frames_thread(sock):
    frame_step = 0
    while not stop_capture:
        frame_step += 1
        ptype, data, addr = frames_queue.get()

        if frame_step >= FRAMES_PER_STEP:
            action = get_action()
            send_action(sock, addr, action)
            frame_step = 0

def main():
    # Initialize the socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PORT))
    
    # Start the keyboard listener thread
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.start()

    # Start threads
    recv_thread = threading.Thread(target=receive_frames_thread, args=(s,))
    process_thread = threading.Thread(target=process_frames_thread, args=(s,))
    recv_thread.start()
    process_thread.start()

    # Wait for threads to finish
    recv_thread.join()
    process_thread.join()
    keyboard_thread.join()

    # Close the connection
    s.close()


if __name__ == '__main__':
    main()