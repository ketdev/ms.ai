import socket
import time
import threading
import zlib
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
FRAME_WIDTH = 512
FRAME_HEIGHT = 288
CAPTURE_TARGET_FPS = 24
FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT

# Packet Constants
HEADER_SIZE = 32
MAX_PACKET_SIZE = 65507

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

    # Receive packet header first
    packet, addr = sock.recvfrom(MAX_PACKET_SIZE)
    if len(packet) < HEADER_SIZE:
        raise Exception("Incomplete packet received")

    # Interpret header data
    # float, float, float, uint64, uint64
    packet_header = packet[:HEADER_SIZE]
    hp, mp, exp, frame_number, length = unpack("fffQQ", packet_header)

    # Receive packet data
    packet_data = packet[HEADER_SIZE:]
    if len(packet_data) < length:
        raise Exception("Incomplete packet received")

    # decompress the packet data with zlib
    packet_data = zlib.decompress(packet_data)

    chunk8bit = unpack_4bit_to_8bit(packet_data)
    frame = np.reshape(chunk8bit, (FRAME_HEIGHT, FRAME_WIDTH))

    return addr, hp, mp, exp, frame_number, frame

def unpack_4bit_to_8bit(packed_array):
    unpacked_size = 2 * len(packed_array)
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

    while not stop_capture:
        addr, hp, mp, exp, frame_number, frame = recv_packet(sock)
        frames_queue.put((addr, frame_number, frame, (hp, mp, exp)))


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
        addr, frame_number, frame, (hp, mp, exp) = frames_queue.get()
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