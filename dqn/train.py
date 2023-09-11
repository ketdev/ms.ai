import sys
import threading
import time
import numpy as np
import queue
import pygame
from capture.screen_capture import get_window_bounds, capture_screen, scale_image, grayscale_image
from capture.keyboard_capture import start_keyboard_listener, KeyState
from model.dqn import DQN

if sys.platform == "darwin":  # macOS
    from capture.input_mac import press_key, release_key
elif sys.platform == "win32":  # Windows
    from capture.input_win import press_virtual_key, release_virtual_key, press_scan_key, release_scan_key

## ==================================================================
## Constants
## ==================================================================

TARGET_WINDOW_NAME = "MapleStory"
GRAYSCALE = True
SCALE = 0.3
TARGET_FPS = 30

FRAMES_PER_STEP = 4
EXPERIENCE_BAR_BOTTOM_OFFSET = 4

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
KEY_ATTACK = 0x21 # 'D'

ACTION_TO_KEY_MAP = {
    Actions.IDLE: None,
    Actions.LEFT: VK_LEFT,
    Actions.RIGHT: VK_RIGHT,
    Actions.UP: VK_UP,
    Actions.DOWN: VK_DOWN,
    Actions.JUMP: KEY_JUMP,
    Actions.ATTACK: KEY_ATTACK
}

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

def is_yellow_green(pixel):
    """Check if a pixel is yellow based on RGB ratio."""
    red, green, blue = pixel[:3]  # only take RGB, ignore alpha if it exists

    # Avoid division by zero
    if green == 0:
        return False

    # Check if the pixel is yellow-green-ish based on ratio
    blue_to_green_ratio = blue / green

    # Check if pixel is light enough
    green_value = green / 255

    return blue_to_green_ratio < 0.7 and green_value > 0.5

def get_experience(screenshot, row_number):
    
    # Convert bytes to numpy array
    frame_width = screenshot.width
    frame_height = screenshot.height
    
    # convert to pixels
    data = screenshot.tobytes()

    # transpose image bytes to same format for make_surface
    data = np.frombuffer(data, dtype=np.uint8)
    data = np.reshape(data, (frame_height, frame_width, 3))
    data = np.transpose(data, (1, 0, 2))

    # read progress bar from image
    row = data[:, row_number, :]

    # turn yellow pixels into white and everything else into black
    first_yellow = None
    last_yellow = None
    for i in range(row.shape[0]):
        if is_yellow_green(row[i]):
            if first_yellow is None:
                first_yellow = i
            last_yellow = i
    
    if first_yellow is None or last_yellow is None:
        return 0.0

    # calculate exp bar percentage
    exp_bar_percentage = (last_yellow - first_yellow) / (row.shape[0] - first_yellow)
    return exp_bar_percentage

def get_new_frame(x, y, w, h, scale):
    frame_width = int(w * scale)
    frame_height = int(h * scale)
    while True:
        screenshot = next(capture_screen(x, y, w, h))

        experience = get_experience(screenshot, frame_height - EXPERIENCE_BAR_BOTTOM_OFFSET)

        # Detect display scaling
        display_scale_down = w / screenshot.width

        # Resize the image to a scale of the original size
        frame = scale_image(screenshot, scale * display_scale_down)
    
        # Convert to grayscale
        frame = grayscale_image(frame)

        # Convert to byte array
        frame = frame.tobytes()

        # Convert bytes to numpy array
        data = np.frombuffer(frame, dtype=np.uint8)
        data = np.reshape(data, (frame_height, frame_width))
        yield data, experience

def get_reward(prev_experience, new_experience):
    if prev_experience is None:
        return 0, True
    # Reward is the difference in experience
    diff = new_experience - prev_experience
    if diff > 0:
        return diff, True
    else: # on level up, the experience bar resets
        return 0, True


def perform_action(prev_action, next_action):
    print(f"Action: {next_action}")

    key = ACTION_TO_KEY_MAP[next_action]

    if next_action == Actions.IDLE:
        pass

    # first presses down, second releases
    elif next_action == Actions.LEFT or \
         next_action == Actions.RIGHT or \
         next_action == Actions.UP or \
         next_action == Actions.DOWN:
        if key not in keys_holding:
            if sys.platform == "darwin":  # macOS
                press_key(key)
            elif sys.platform == "win32":  # Windows
                press_virtual_key(key)
        else:
            if sys.platform == "darwin":  # macOS
                release_key(key)
            elif sys.platform == "win32":  # Windows
                release_virtual_key(key)
    elif next_action == Actions.JUMP or \
         next_action == Actions.ATTACK:
        if key not in keys_holding:
            if sys.platform == "darwin":  # macOS
                press_key(key)
            elif sys.platform == "win32":  # Windows
                press_scan_key(key)
        else:
            if sys.platform == "darwin":  # macOS
                release_key(key)
            elif sys.platform == "win32":  # Windows
                release_scan_key(key)


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
        new_frame, experience = next(get_new_frame(x, y, w, h, SCALE))
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
    prev_experience = None

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
        new_frame, new_experience = next(get_new_frame(x, y, w, h, SCALE))
        frames = np.roll(frames, -1, axis=2)
        frames[:, :, -1] = new_frame

        print(f"Experience: {new_experience * 100:.2f}%")

        # State is 1 frame set of 4 frames
        next_state = np.reshape(frames, [1, state_shape[0], state_shape[1], state_shape[2]])

        # Get reward and done from game environment for previous action
        reward, done = get_reward(prev_experience, new_experience)

        # Store previous state, action, reward, next_state, done in agent memory
        agent.remember(prev_state, prev_action, reward, next_state, done)

        # Get action from DQN agent
        next_action = agent.act(prev_state)

        # Perform action in game environment
        perform_action(prev_action, next_action)

        # Update previous state
        prev_state = next_state
        prev_action = next_action
        prev_experience = new_experience

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
