import time
from pynput import keyboard

## ==================================================================
## Constants
## ==================================================================

class KeyState:
    PRESS = 0
    RELEASE = 1

## ==================================================================
## Get Keyboard Actions
## ==================================================================

# Keyboard listener
def on_key_press(key, queue, stop_capture_func):
    if stop_capture_func():
        return False
    try:
        queue.put((time.time(), KeyState.PRESS, key.char))
    except AttributeError:
        queue.put((time.time(), KeyState.PRESS, key.name))

def on_key_release(key, queue, stop_capture_func):
    if stop_capture_func():
        return False
    try:
        queue.put((time.time(), KeyState.RELEASE, key.char))
    except AttributeError:
        queue.put((time.time(), KeyState.RELEASE, key.name))

# Start keyboard listeners
def start_keyboard_listener(queue, stop_capture_func):
    # bind queue and stop_capture_func to on_key_press and on_key_release
    on_key_press_func = lambda key: on_key_press(key, queue, stop_capture_func)
    on_key_release_func = lambda key: on_key_release(key, queue, stop_capture_func)
    with keyboard.Listener(on_press=on_key_press_func, on_release=on_key_release_func) as listener:
        listener.join()

