import random
import socket
import time
import threading
import zlib
import numpy as np
import struct
from struct import unpack
from pynput import keyboard
from collections import deque
from queue import Queue

from model.config import PORT, FRAME_WIDTH, FRAME_HEIGHT, \
    FRAME_PACKET_HEADER_SIZE, MAX_PACKET_SIZE, MAX_KEYS, \
    FRAMES_PER_STEP, Actions, ACTION_TO_KEY_MAP

from model.debug_display import initialize_display, display_loop, update_display, post_quit_event, close_display
from model.model_interface import init_model_interface, reward_model, get_actions, replay_learning, model_stop

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
            post_quit_event()
            return False
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()


## ==================================================================
## Frame Input Logic
## ==================================================================

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
        # Receive packet header first
        packet, addr = sock.recvfrom(MAX_PACKET_SIZE)
        if len(packet) < FRAME_PACKET_HEADER_SIZE:
            raise Exception("Incomplete packet received")

        # Interpret header data
        # float, float, float, uint64, uint64
        packet_header = packet[:FRAME_PACKET_HEADER_SIZE]
        hp, mp, exp, frame_number, length = unpack("fffQQ", packet_header)

        # Receive packet data
        packet_data = packet[FRAME_PACKET_HEADER_SIZE:]
        if len(packet_data) < length:
            raise Exception("Incomplete packet received")

        # decompress the packet data with zlib
        packet_data = zlib.decompress(packet_data)

        chunk8bit = unpack_4bit_to_8bit(packet_data)
        frame = np.reshape(chunk8bit, (FRAME_HEIGHT, FRAME_WIDTH))

        frames_queue.put((addr, frame_number, frame, (hp, mp, exp)))


## ==================================================================
## Model & Action Logic
## ==================================================================

def send_action_packet(sock, addr, actions_toggle):
    # translate actions to keys
    keys = []
    for action_index, action in enumerate(actions_toggle):
        if action:
            keys.append(ACTION_TO_KEY_MAP[action_index])

    # Fill the rest of the packet with zeros (no keys)
    while len(keys) < MAX_KEYS:
        keys.append((0, 0))

    action_packet = b''.join(struct.pack('bb', key[0], key[1]) for key in keys)
    sock.sendto(action_packet, addr)

def process_frames_thread(sock, screen):
    frame_step = 0

    metrics = deque(maxlen=FRAMES_PER_STEP)
    frames = deque(maxlen=FRAMES_PER_STEP)
    action_vector = np.zeros(Actions._SIZE, dtype=np.float32)
    action_index = 0 # picked action index

    # Initialize counters
    frame_count = 0
    prev_frames = None
    prev_action_index = None

    # Actions toggle
    actions_toggle = np.zeros(Actions._SIZE, dtype=np.uint8)

    # Count frames per second
    fps = 0
    last_time = time.time()

    while not stop_capture:
        addr, frame_number, frame, (hp, mp, exp) = frames_queue.get()
        frame_step += 1

        # accumulate frames
        frames.append(frame)
        metrics.append((hp, mp, exp))
                    
        if frame_step >= FRAMES_PER_STEP:

            # turn frames to numpy array
            frames_array = np.array(frames, dtype=np.uint8)   
            frames_array = np.transpose(frames_array, (1, 2, 0))       

            # Reward the model for previous action
            reward_model(prev_frames, prev_action_index, metrics, frames_array)

            # Process the frames and get the next action
            action_vector, action_index = get_actions(frames_array)

            # Toggle actions
            actions_toggle[action_index] = not actions_toggle[action_index]

            # Send the action packet to the game
            send_action_packet(sock, addr, actions_toggle)

            # Update counters
            prev_frames = frames_array
            prev_action_index = action_index
            frame_count += 1
            frame_step = 0

            # Signal replay learning if needed
            replay_learning(frame_count)

        # Update the display
        update_display(screen, frames, hp, mp, exp, action_vector, action_index)

        # Report FPS
        if frame_count % 100 == 0:
            cur_time = time.time()
            fps = 100 / (cur_time - last_time)
            last_time = cur_time
            print("FPS: {}".format(fps))


## ==================================================================
## Main Processes
## ==================================================================

def main():
    # Initialize the socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PORT))

    # Initialize the game interface
    screen = initialize_display()

    # Initialize model training
    init_model_interface()

    # Start threads
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    recv_thread = threading.Thread(target=receive_frames_thread, args=(s,))
    process_thread = threading.Thread(target=process_frames_thread, args=(s,screen,))
    recv_thread.start()
    process_thread.start()
    keyboard_thread.start()

    # Start the display loop
    display_loop()

    # Wait for threads to finish
    recv_thread.join()
    process_thread.join()
    keyboard_thread.join()

    # Close the connection
    s.close()

    # Close the display
    close_display()


if __name__ == '__main__':
    main()