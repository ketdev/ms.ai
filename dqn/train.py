import threading
import time
import numpy as np
import queue
import pygame
from capture.screen_capture import get_window_bounds, screen_capture_generator
from capture.keyboard_capture import start_keyboard_listener, KeyState
from model.dqn import DQN

## ==================================================================
## Constants
## ==================================================================

TARGET_WINDOW_NAME = "Sourcetree"
TARGET_FPS = 30
GRAYSCALE = True
SCALE = 0.3
FRAMES_PER_STEP = 4

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

# Derived constants
FRAME_DELAY = 1.0 / TARGET_FPS

## ==================================================================
## Global Variables
## ==================================================================

# Global stop flag for threads
stop_capture = False

# Global event for replay
can_replay = threading.Event()

## ==================================================================
## Logic
## ==================================================================

def get_new_frame(x, y, w, h, scale, grayscale):
    frame_width = int(w * SCALE)
    frame_height = int(h * SCALE)
    while True:
        screenshot = next(screen_capture_generator(x, y, w, h, scale, grayscale))
        # Convert bytes to numpy array
        data = np.frombuffer(screenshot, dtype=np.uint8)
        data = np.reshape(data, (frame_height, frame_width))
        yield data

def get_reward(prev_state, action, next_state):
    # TODO: Implement reward function
    return 0, False  # Reward, Done


def perform_action(prev_action, next_action):
    # TODO: Implement action function
    print(f"Action: {next_action}")


def train_agent():
    while not stop_capture:
        can_replay.wait()  # Wait until main loop signals a replay is possible
        if len(agent.memory) > BATCH_SIZE:
            agent.replay(BATCH_SIZE)
            can_replay.clear()  # Reset the event flag


## ==================================================================
## Display Logic with Pygame
## ==================================================================

def initialize_display(width, height):
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption('Captured Frames')
    return screen

def display_frames(screen, frames):
    # Transpose and enumerate the frames
    for i, frame in enumerate(frames.transpose(2, 1, 0)):
        frame = np.stack([frame] * 3, -1)
        frame_surface = pygame.surfarray.make_surface(frame)
        # draw from right to left
        screen.blit(frame_surface, (screen.get_width() - (i + 1) * frame_surface.get_width(), 0))
    pygame.display.flip()
    

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
    x = bounds["position"]["x"]
    y = bounds["position"]["y"]
    w = bounds["size"]["width"]
    h = bounds["size"]["height"]
    print(f"Found: {title} (x:{x} y:{y} w:{w} h:{h})")

    # Get initial state from game environment
    frames = []
    for i in range(FRAMES_PER_STEP):
        new_frame = next(get_new_frame(x, y, w, h, SCALE, GRAYSCALE))
        if i == 0:
            frames = np.zeros((new_frame.shape[0], new_frame.shape[1], FRAMES_PER_STEP), dtype=np.uint8)
        frames[:, :, i] = new_frame

    # Initialize Pygame display
    frame_width = frames.shape[1]
    frame_height = frames.shape[0]
    screen = initialize_display(frame_width * FRAMES_PER_STEP, frame_height)

    # Initialize DQN agent
    state_shape = (frames.shape[0], frames.shape[1], frames.shape[2])
    agent = DQN(state_shape, Actions._SIZE)
    agent.model.summary()

    # State is 1 frame set of 4 frames
    prev_state = np.reshape(frames, [1, state_shape[0], state_shape[1], state_shape[2]])
    prev_action = Actions.IDLE

    # Run DQN agent
    frame_count = 0
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
        new_frame = next(get_new_frame(x, y, w, h, SCALE, GRAYSCALE))
        frames = np.roll(frames, -1, axis=2)
        frames[:, :, -1] = new_frame

        # State is 1 frame set of 4 frames
        next_state = np.reshape(frames, [1, state_shape[0], state_shape[1], state_shape[2]])

        # Get reward and done from game environment for previous action
        reward, done = get_reward(prev_state, prev_action, next_state)

        # Store previous state, action, reward, next_state, done in agent memory
        agent.remember(prev_state, prev_action, reward, next_state, done)

        # Get action from DQN agent
        next_action = agent.act(prev_state)

        # Perform action in game environment
        perform_action(prev_action, next_action)

        # Update previous state
        prev_state = next_state
        prev_action = next_action

        # Check if the agent can replay
        if len(agent.memory) > BATCH_SIZE:
            can_replay.set()  # Signal to the training thread that it can start a replay

        frame_count += 1

        if frame_count % UPDATE_TARGET_MODEL_EVERY == 0:
            agent.update_target_model()

        if frame_count % SAVE_WEIGHTS_EVERY == 0:
            agent.save(f"dqn_weights_{frame_count}.h5")  # save with the frame count for clarity

        # Display the frames using pygame
        display_frames(screen, frames)
        
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
