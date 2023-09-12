import os
import sys
import threading
import time
import numpy as np
from capture.screen_capture import get_window_bounds, capture_screen, scale_image, grayscale_image, to_numpy_rgb, to_numpy_grayscale
from logic.metrics import get_metric_percentages
from logic.debug_display import initialize_display, display_frames, display_event_loop, close_display
from logic.config import TARGET_WINDOW_NAME, SCALE, \
    WINDOW_MARGIN_BOTTOM, WINDOW_MARGIN_LEFT, WINDOW_MARGIN_RIGHT, WINDOW_MARGIN_TOP, \
    ACTION_TO_KEY_MAP, Actions

if sys.platform == "darwin":  # macOS
    from capture.input_mac import press_key, release_key
elif sys.platform == "win32":  # Windows
    from capture.input_win import press_virtual_key, release_virtual_key, press_scan_key, release_scan_key

## ==================================================================
## Constants
## ==================================================================

DISPLAY_SCALE = 2
DISPLAY_EXP_BAR_HEIGHT = 20 
DISPLAY_ACTION_PROB_HEIGHT = 100

## ==================================================================
## Global Variables
## ==================================================================

# Window bounds
window_x, window_y, window_w, window_h = 0, 0, 0, 0

# Screen 
screen = None

# Keys pressed down
keys_holding = []

## ==================================================================

def init_game_interface():
    global window_x, window_y, window_w, window_h
    global screen

    # Get bounds for target window
    title, bounds = get_window_bounds(TARGET_WINDOW_NAME).popitem()
    x = bounds["position"]["x"] + WINDOW_MARGIN_LEFT
    y = bounds["position"]["y"] + WINDOW_MARGIN_TOP
    w = bounds["size"]["width"] - (WINDOW_MARGIN_LEFT + WINDOW_MARGIN_RIGHT)
    h = bounds["size"]["height"] - (WINDOW_MARGIN_TOP + WINDOW_MARGIN_BOTTOM)
    print(f"Found: {title} (x:{x} y:{y} w:{w} h:{h})")
    window_x, window_y, window_w, window_h = x, y, w, h

    # Initialize Pygame display
    frame_width = w * SCALE
    frame_height = h * SCALE
    screen = initialize_display(frame_width * (1 + 1/3), frame_height)


def capture_frame():
    while True:
        screenshot = next(capture_screen(window_x, window_y, window_w, window_h))
        img_data = to_numpy_rgb(screenshot) # np array

        # Calculate metrics from screenshot
        metrics = get_metric_percentages(img_data)

        # Frame is scaled down grayscale image
        display_scale_down = window_w / screenshot.width
        frame = scale_image(screenshot, SCALE * display_scale_down)
        frame = grayscale_image(frame)
        data = to_numpy_grayscale(frame)

        yield data, metrics

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

def display_info(frames, metrics, action_vector, action, fps):
    display_frames(screen, frames, metrics, action_vector, action, fps)
    display_event_loop()
