
import numpy as np
from collections import deque

from model.config import FRAMES_PER_STEP, Actions

## ==================================================================
## Manual Control Entry
## ==================================================================

def manual_control_entry(stop_event, frame_queue, action_queue, display_queue, input_keys_queue):
    frame_step = 0
    frames = deque(maxlen=FRAMES_PER_STEP)

    action_states = np.zeros(Actions._SIZE, dtype=np.uint8)
    action_vector = np.zeros(Actions._SIZE, dtype=np.float32)
    action_index = 0 # picked action index

    while not stop_event.is_set():

        # Get the next frame
        try:
            addr, frame_number, frame, metrics, frame_action_state = frame_queue.get(timeout=1)
        except:
            continue

        # Handle any input keys without blocking
        while not input_keys_queue.empty():
            key, state = input_keys_queue.get()   
            action_index = Actions.IDLE
            if key == 'left':
                action_index = Actions.LEFT
            elif key == 'right':
                action_index = Actions.RIGHT
            elif key == 'up':
                action_index = Actions.UP
            elif key == 'down':
                action_index = Actions.DOWN
            elif key == 'a':
                action_index = Actions.ATTACK
            elif key == 'd':
                action_index = Actions.JUMP

            # Update action states, toggle the action
            action_states[action_index] = state

        # accumulate data
        frames.append(frame)
        frame_step += 1

        # Send data to update display
        display_queue.put((frames, metrics, action_states, action_vector, action_index))

        if frame_step >= FRAMES_PER_STEP:

            # Queue action for the game
            action_queue.put((addr, action_states))

            # Update counters
            frame_step = 0
