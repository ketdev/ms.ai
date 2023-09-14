import socket
import time
import threading
import numpy as np
from struct import unpack
from pynput import keyboard
from queue import Queue

from logic.debug_display import initialize_display, draw_frame, display_flip

## ==================================================================
## Configurations
## ==================================================================

# Network
PORT = 12345

# Environment
FRAME_WIDTH = 400
FRAME_HEIGHT = 225
CAPTURE_TARGET_FPS = 20
FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT

# Packet Constants
PACKET_SIZE = 45000 + 8
NUMBER_OF_ROWS = FRAME_HEIGHT

METRICS_TYPE = 0
CHUNK_TYPE = 1

METRICS_SIZE = 3 * 4  # Three float32 values

# Action space
FRAMES_PER_STEP = 4

class Actions:
    IDLE = 0
    ATTACK = 1
    LEFT = 2
    RIGHT = 3
    # UP = 3
    # DOWN = 4
    # JUMP = 5
    _SIZE = 4

MODEL_WEIGHTS_FILE = "model_weights.h5"




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
## Input Logic
## ==================================================================

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
        data = packet[8:]
        data = np.frombuffer(data, dtype=np.uint8)
        chunk = (row, data)
        return CHUNK_TYPE, chunk, addr

def unpack_4bit_to_8bit(packed_array):
    unpacked_size = 2 * packed_array.size
    unpacked_array = np.zeros(unpacked_size, dtype=np.uint8)

    for i, val in enumerate(packed_array):
        # Extract the two 4-bit values from the packed byte
        pixel1 = (val & 0xF0) >> 4
        pixel2 = val & 0x0F

        # Convert the 4-bit values to 8-bit by repeating the same 4 bits
        unpacked_array[2*i] = pixel1 << 4
        unpacked_array[2*i + 1] = pixel2 << 4
        
    return unpacked_array

def receive_frames_thread(sock):

    # reconstruct the frame from chunks
    frame_counter = 0
    frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.uint8)
    metrics = None

    while not stop_capture:
        ptype, data, addr = recv_packet(sock)

        # If packet is a metrics packet, complete last frame and start a new frame
        if ptype == METRICS_TYPE:

            # complete last frame
            if metrics is not None:
                frames_queue.put((addr, frame_counter, frame, metrics))
                # frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.uint8)

            # start a new frame
            frame_counter += 1
            metrics = data
            print(metrics)

        # If packet is a frame chunk packet, reconstruct the frame
        if ptype == CHUNK_TYPE:
            index, chunk4bit = data
            chunk8bit = unpack_4bit_to_8bit(chunk4bit)

            # chunk can be multiple rows of pixels, write to frame
            row = index * NUMBER_OF_ROWS

            # Write all rows of the chunk to the frame
            for i in range(NUMBER_OF_ROWS):
                frame[row + i] = chunk8bit[i*FRAME_WIDTH:(i+1)*FRAME_WIDTH]


## ==================================================================
## Action Logic
## ==================================================================

def get_action():
    # For the sake of simplicity, this function will just
    # return a dummy action byte. Replace with your own logic!
    dummy_action = b'0'
    return dummy_action


def send_action(sock, addr, action):
    sock.sendto(action, addr)

def process_frames_thread(sock, screen):

    frame_step = 0
    while not stop_capture:
        addr, frame_counter, frame, metrics = frames_queue.get()
        frame_step += 1

        # clear the screen
        screen.fill((0, 0, 0))

        # draw the frame
        draw_frame(screen, frame)

        if frame_step >= FRAMES_PER_STEP:
            action = get_action()
            send_action(sock, addr, action)
            frame_step = 0

        # update the screen
        display_flip()

## ==================================================================
## Main Processes
## ==================================================================


def main():
    # Initialize the socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PORT))

    # Start the keyboard listener thread
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.start()

    # Initialize the game interface
    screen = initialize_display(FRAME_WIDTH, FRAME_HEIGHT)

    # Start threads
    recv_thread = threading.Thread(target=receive_frames_thread, args=(s,))
    process_thread = threading.Thread(target=process_frames_thread, args=(s,screen,))
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