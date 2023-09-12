import os
import sys
import threading
import time
import numpy as np
import queue
import pygame
from capture.screen_capture import get_window_bounds, capture_screen, scale_image, grayscale_image, to_numpy_rgb, to_numpy_grayscale
from capture.keyboard_capture import start_keyboard_listener, KeyState
from logic.metrics import get_metric_percentages
from logic.debug_display import initialize_display, display_frames
from model.dqn import DQN

if sys.platform == "darwin":  # macOS
    from capture.input_mac import press_key, release_key
elif sys.platform == "win32":  # Windows
    from capture.input_win import press_virtual_key, release_virtual_key, press_scan_key, release_scan_key

## ==================================================================
## Constants
## ==================================================================

TARGET_WINDOW_NAME = "Sourcetree"
MODEL_WEIGHTS_FILE = "model_weights.h5"
GRAYSCALE = True
SCALE = 0.3
TARGET_FPS = 30

DISPLAY_SCALE = 2
FRAMES_PER_STEP = 4
DISPLAY_EXP_BAR_HEIGHT = 20 
DISPLAY_ACTION_PROB_HEIGHT = 100

class Actions:
    IDLE = 0
    LEFT = 1
    RIGHT = 2
    UP = 3
    DOWN = 4
    JUMP = 5
    ATTACK = 6
    _SIZE = 7

# DQN Constants
BATCH_SIZE = 32
UPDATE_TARGET_MODEL_EVERY = 1000
SAVE_WEIGHTS_EVERY = 5000  # Save model weights every 5000 frames

# Action Virtual key codes
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
# Action Scan codes
KEY_JUMP = 0x1E # 'A'
KEY_ATTACK = 0x20 # 'D'

ACTION_TO_KEY_MAP = {
    Actions.IDLE: None,
    Actions.LEFT: VK_LEFT,
    Actions.RIGHT: VK_RIGHT,
    Actions.UP: VK_UP,
    Actions.DOWN: VK_DOWN,
    Actions.JUMP: KEY_JUMP,
    Actions.ATTACK: KEY_ATTACK
}

# Window capture margins
WINDOW_MARGIN_LEFT = 11
WINDOW_MARGIN_TOP = 45
WINDOW_MARGIN_RIGHT = 11
WINDOW_MARGIN_BOTTOM = 11

# Derived constants
FRAME_DELAY = 1.0 / TARGET_FPS

## ==================================================================
## Global Variables
## ==================================================================

# Global stop flag for threads
stop_capture = False

# Global event for replay
can_replay = threading.Event()

# Keys pressed down
keys_holding = []

## ==================================================================
## Logic
## ==================================================================

def get_state(x, y, w, h):
    while True:
        screenshot = next(capture_screen(x, y, w, h))
        img_data = to_numpy_rgb(screenshot) # np array

        # Calculate metrics from screenshot
        metrics = get_metric_percentages(img_data)

        # Frame is scaled down grayscale image
        display_scale_down = w / screenshot.width
        frame = scale_image(screenshot, SCALE * display_scale_down)
        frame = grayscale_image(frame)
        data = to_numpy_grayscale(frame)

        yield data, metrics

def get_reward(prev_metrics, next_metrics):
    done = False
    if prev_metrics is None:
        return 0, done

    # Reward when experience bar increases
    prev_experience = prev_metrics["EXP"]
    new_experience = next_metrics["EXP"]
    exp_reward = (new_experience - prev_experience) * 100
    exp_reward = max(exp_reward, 0)
    # Punish when health bar decreases
    prev_health = prev_metrics["HP"]
    new_health = next_metrics["HP"]
    damage_punish = (prev_health - new_health) * 10
    damage_punish = max(damage_punish, 0)
    
    return exp_reward - damage_punish, done

def perform_action(prev_action, next_action):
    print(f"Action: {next_action}")

    key = ACTION_TO_KEY_MAP[next_action]

    if next_action == Actions.IDLE:
        pass

    # first presses down, second releases
    
         #next_action == Actions.UP or \
    elif next_action == Actions.LEFT or \
         next_action == Actions.RIGHT or \
         next_action == Actions.DOWN:
        if key not in keys_holding:
            if sys.platform == "darwin":  # macOS
                press_key(key)
            elif sys.platform == "win32":  # Windows
                press_virtual_key(key)
            keys_holding.append(key)
        else:
            if sys.platform == "darwin":  # macOS
                release_key(key)
            elif sys.platform == "win32":  # Windows
                release_virtual_key(key)
            keys_holding.remove(key)
    elif next_action == Actions.ATTACK or \
         next_action == Actions.JUMP:
        if key not in keys_holding:
            if sys.platform == "darwin":  # macOS
                press_key(key)
            elif sys.platform == "win32":  # Windows
                press_scan_key(key)
            keys_holding.append(key)
        else:
            if sys.platform == "darwin":  # macOS
                release_key(key)
            elif sys.platform == "win32":  # Windows
                release_scan_key(key)
            keys_holding.remove(key)

def train_agent():
    while not stop_capture:
        can_replay.wait()  # Wait until main loop signals a replay is possible
        if len(agent.memory) > BATCH_SIZE:
            agent.replay(BATCH_SIZE)
            can_replay.clear()  # Reset the event flag


## ==================================================================
## Main
## ==================================================================

if __name__ == '__main__':

    # Start keyboard listener
    keyboard_queue = queue.Queue()
    keyboard_thread = threading.Thread(target=start_keyboard_listener, args=(keyboard_queue, lambda: stop_capture))
    keyboard_thread.start()

    # Start the agent training thread
    training_thread = threading.Thread(target=train_agent)
    training_thread.start()
    
    # Get bounds for target window
    title, bounds = get_window_bounds(TARGET_WINDOW_NAME).popitem()
    x = bounds["position"]["x"] + WINDOW_MARGIN_LEFT
    y = bounds["position"]["y"] + WINDOW_MARGIN_TOP
    w = bounds["size"]["width"] - (WINDOW_MARGIN_LEFT + WINDOW_MARGIN_RIGHT)
    h = bounds["size"]["height"] - (WINDOW_MARGIN_TOP + WINDOW_MARGIN_BOTTOM)
    print(f"Found: {title} (x:{x} y:{y} w:{w} h:{h})")

    # Get initial state from game environment
    frames = []
    for i in range(FRAMES_PER_STEP):
        next_frame, metrics = next(get_state(x, y, w, h))
        if i == 0:
            frames = np.zeros((next_frame.shape[0], next_frame.shape[1], FRAMES_PER_STEP), dtype=np.uint8)
        frames[:, :, i] = next_frame

    # Initialize Pygame display
    frame_width = frames.shape[0]
    frame_height = frames.shape[1]
    screen = initialize_display(frame_width * (1 + 1/3), frame_height)

    # Initialize DQN agent
    state_shape = (frames.shape[0], frames.shape[1], frames.shape[2])
    agent = DQN(state_shape, Actions._SIZE)
    agent.model.summary()

    # Load model weights if exists
    if os.path.exists(MODEL_WEIGHTS_FILE):
        agent.load(MODEL_WEIGHTS_FILE)

    # State is 1 frame set of 4 frames
    prev_state = np.reshape(frames, [1, state_shape[0], state_shape[1], state_shape[2]])
    prev_action = Actions.IDLE
    prev_metrics = None

    # Keep track of frames per second
    frame_count = 0
    fps_start_time = time.time()
    fps = 0

    # Run DQN agent
    while not stop_capture:
        timestamp = time.time()

        # Check if ESC key was pressed
        try:
            key_timestamp, key_state, key = keyboard_queue.get(block=False)
            if key_state == KeyState.PRESS and key == "esc":
                stop_capture = True
        except queue.Empty:
            pass

        # Get next state from game environment
        next_frame, next_metrics = next(get_state(x, y, w, h))
        frames = np.roll(frames, -1, axis=2)
        frames[:, :, -1] = next_frame

        # State is 1 frame set of 4 frames
        next_state = np.reshape(frames, [1, state_shape[0], state_shape[1], state_shape[2]])

        # Get reward and done from game environment for previous action
        reward, done = get_reward(prev_metrics, next_metrics)
        
        if reward > 0:
            print(f"REWARD: {reward}")

        # Store previous state, action, reward, next_state, done in agent memory
        agent.remember(prev_state, prev_action, reward, next_state, done)

        # Get action from DQN agent
        next_action_vector = agent.predict(next_state)
        next_action = agent.act(next_action_vector)

        # Perform action in game environment
        perform_action(prev_action, next_action)

        # Update previous state
        prev_state = next_state
        prev_action = next_action
        prev_metrics = next_metrics

        frame_count += 1

        # Update frames per second
        if time.time() - fps_start_time >= 1:
            fps = frame_count
            frame_count = 0
            fps_start_time = time.time()

        # # Check if the agent can replay
        if len(agent.memory) > BATCH_SIZE:
            can_replay.set()  # Signal to the training thread that it can start a replay

        if frame_count % UPDATE_TARGET_MODEL_EVERY == 0:
            agent.update_target_model()

        if frame_count % SAVE_WEIGHTS_EVERY == 0:
            agent.save(f"dqn_weights_{frame_count}.h5")  # save with the frame count for clarity

        # Display the frames using pygame
        display_frames(screen, frames, next_metrics, next_action_vector, next_action, fps)
        
        # Add event handling to close pygame window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_capture = True

        # Calculate remaining delay to maintain 30 fps
        elapsed_time = time.time() - timestamp
        sleep_time = FRAME_DELAY - elapsed_time
        if sleep_time > 0:
            time.sleep(sleep_time)

    # Gracefully stop the threads
    training_thread.join()
    keyboard_thread.join()

    # Quit pygame
    pygame.quit()

    # Save model weights at end of training
    agent.save("dqn_weights_final.h5")

    print("Done")
