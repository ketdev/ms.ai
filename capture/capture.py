import io
import sys
import time
import threading
import queue
import mss
from PIL import Image
from pynput import mouse, keyboard
if sys.platform == "darwin":  # macOS
    from appscript import app
elif sys.platform == "win32":  # Windows
    import win32gui
import msgpack

## ==================================================================
## Constants
## ==================================================================

FILENAME = 'game_data.mpk'
TARGET_WINDOW_NAME = "MapleStory"
TARGET_FPS = 30
GRAYSCALE = True
SCALE = 0.3

class InputType:
    MOUSE = 0
    KEYBOARD = 1

class KeyState:
    PRESS = 0
    RELEASE = 1
    MOVE = 2
    SCROLL = 3

## ==================================================================
## Global variables
## ==================================================================

## Global stop flag for threads
stop_capture = False

# Shared queue for screen frames
data_queue = queue.Queue()

# Individual queues for mouse and keyboard actions
input_actions = queue.Queue()

# Save the window bounds for calculating relative mouse position
window_bound = {}

## ==================================================================
## Get window information
## ==================================================================

def get_all_window_titles():
    titles = []
    if sys.platform == "darwin":  # macOS
        system_events = app("System Events")
        for process in system_events.processes():
            for window in process.windows():
                titles.append(window.name())
    elif sys.platform == "win32":  # Windows
        def win_get_titles(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                titles.append(win32gui.GetWindowText(hwnd))
        win32gui.EnumWindows(win_get_titles, None)
    return titles

def get_window_bounds(title=None):
    bounds = {}
    if sys.platform == "darwin":  # macOS
        system_events = app("System Events")
        for process in system_events.processes():
            for window in process.windows():
                if (title and title == window.name()) or not title:
                    position = window.position.get()
                    size = window.size.get()
                    bounds[window.name()] = {
                        "position": {
                            "x": position[0],
                            "y": position[1]
                        },
                        "size": {
                            "width": size[0],
                            "height": size[1]
                        }
                    }

    elif sys.platform == "win32":  # Windows
        def win_get_bounds(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                rect = win32gui.GetWindowRect(hwnd)
                if (title and title == win32gui.GetWindowText(hwnd)) or not title:
                    bounds[win32gui.GetWindowText(hwnd)] = {
                        "position": {
                            "x": rect[0],
                            "y": rect[1]
                        },
                        "size": {
                            "width": rect[2] - rect[0],
                            "height": rect[3] - rect[1]
                        }
                    }
        win32gui.EnumWindows(win_get_bounds, None)
    return bounds

## ==================================================================
## Screen Capture
## ==================================================================

## Capture screen using mss on a separate thread
def start_capture_screen(bounds, fps):
    global stop_capture
    delay = 1.0 / fps
    with mss.mss() as sct:
        while not stop_capture:
            start_time = time.time()
            
            top = bounds["position"]["y"]
            left = bounds["position"]["x"]
            width = bounds["size"]["width"]
            height = bounds["size"]["height"]
            
            timestamp = time.time()
            screenshot = sct.grab({"top": top, "left": left, "width": width, "height": height})

            # Save to the picture file
            # mss.tools.to_png(screenshot.rgb, screenshot.size, output='screenshot.png')

            # Convert to PIL from mss
            rgb = screenshot.rgb
            size = (screenshot.width, screenshot.height)
            pil_image = Image.frombytes('RGB', size, rgb)
            
            # Resize the image to 30% of the original size
            pil_image = pil_image.resize((int(pil_image.width * SCALE), int(pil_image.height * SCALE)), Image.LANCZOS)
            
            # Convert to grayscale
            if GRAYSCALE:
                pil_image = pil_image.convert('L')
            else:
                pil_image = pil_image.convert('RGB')

            # # Convert to byte array
            # rgb_im = pil_image.tobytes()

            # Compress image using PNG
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            compressed_image_data = buffer.getvalue()

            # Put the image data into the queue
            data_queue.put({
                "timestamp": timestamp,
                "frame": compressed_image_data
            })

            # Calculate remaining delay to maintain 30 fps
            elapsed_time = time.time() - start_time
            sleep_time = delay - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)


## ==================================================================
## Get Mouse and Keyboard Actions
## ==================================================================

# Mouse listener
def on_move(x, y):
    if stop_capture:
        return False
    # Calculate relative position
    x = x - window_bound["position"]["x"]
    y = y - window_bound["position"]["y"]

    # # Print pointer position
    # print('Pointer moved to {0}'.format((x, y)))
    # mouse_actions.put((KeyState.MOVE, x, y))

def on_click(x, y, button, pressed):
    if stop_capture:
        return False
    # Calculate relative position
    x = x - window_bound["position"]["x"]
    y = y - window_bound["position"]["y"]

    # # Print click information
    # print('{0} at {1}'.format('Pressed' if pressed else 'Released', (x, y)))
    if pressed:
        input_actions.put((time.time(), InputType.MOUSE, KeyState.PRESS, x, y, button.name))
    else:
        input_actions.put((time.time(), InputType.MOUSE, KeyState.RELEASE, x, y, button.name))

def on_scroll(x, y, dx, dy):
    if stop_capture:
        return False
    # Calculate relative position
    x = x - window_bound["position"]["x"]
    y = y - window_bound["position"]["y"]
    # # Print scroll direction
    # print('Scrolled {0} at {1}'.format('down' if dy < 0 else 'up',(x, y)))
    input_actions.put((time.time(), InputType.MOUSE, KeyState.SCROLL, x, y, dx, dy))

# Keyboard listener
def on_key_press(key):
    global stop_capture
    if stop_capture:
        return False
    # Stop capturing if ESC is pressed
    if key == keyboard.Key.esc:
        stop_capture = True
        return False
    # # Print key pressed
    # try:
    #     print('alphanumeric key {0} pressed'.format(
    #         key.char))
    # except AttributeError:
    #     print('special key {0} pressed'.format(
    #         key))
    # use char or name if char doesn't exist
    try:
        input_actions.put((time.time(), InputType.KEYBOARD, KeyState.PRESS, key.char))
    except AttributeError:
        input_actions.put((time.time(), InputType.KEYBOARD, KeyState.PRESS, key.name))

def on_key_release(key):
    if stop_capture:
        return False
    # # Print key released
    # print('{0} released'.format(key))
    # use char or name if char doesn't exist
    try:
        input_actions.put((time.time(), InputType.KEYBOARD, KeyState.RELEASE, key.char))
    except AttributeError:
        input_actions.put((time.time(), InputType.KEYBOARD, KeyState.RELEASE, key.name))

# Function to start mouse listener
def start_mouse_listener():
    with mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll) as listener:
        listener.join()

# Function to start keyboard listener
def start_keyboard_listener():
    with keyboard.Listener(on_press=on_key_press, on_release=on_key_release) as listener:
        listener.join()


## ==================================================================
## Main
## ==================================================================

def synchronize_data(data_queue, input_actions):
    combined_data = []

    while not data_queue.empty():
        frame_data = data_queue.get()
        frame_timestamp = frame_data['timestamp']
        next_frame_timestamp = None
        if not data_queue.empty():
            # Peek at the next timestamp without actually removing it from the queue
            next_frame_timestamp = data_queue.queue[0]['timestamp']

        actions_for_frame = []
        # Extract actions that fit between current frame and next frame
        while True:
            if input_actions.empty():
                break
            
            # Peek at the top action's timestamp without actually removing it
            action_timestamp = input_actions.queue[0][0]
            if next_frame_timestamp is None or action_timestamp < next_frame_timestamp:
                actions_for_frame.append(input_actions.get())
            else:
                break

        frame_data["actions"] = actions_for_frame
        combined_data.append(frame_data)

    return combined_data

def main():
    global stop_capture
    
    titles = get_all_window_titles()

    # find title that includes our target
    found_title = None
    for title in titles:
        if TARGET_WINDOW_NAME == title:
            found_title = title
            break
    print(f"Found title: {found_title}")

    # To get bounds for a specific window by title
    bounds = get_window_bounds(found_title)
    
    for title, bound in bounds.items():
        global window_bound
        window_bound = bound
        print(f"Title: {title}")
        print(f"Position: {bound['position']}")
        print(f"Size: {bound['size']}")

    # Create threads for each task
    screen_thread = threading.Thread(target=start_capture_screen, args=(bounds[found_title], TARGET_FPS))
    mouse_thread = threading.Thread(target=start_mouse_listener)
    keyboard_thread = threading.Thread(target=start_keyboard_listener)

    # Start all threads
    screen_thread.start()
    mouse_thread.start()
    keyboard_thread.start()

    # Wait for all threads to finish
    for thread in [screen_thread, mouse_thread, keyboard_thread]:
        thread.join()


    # Before saving to file, combine the queues
    combined_data = synchronize_data(data_queue, input_actions)

    # Save data to a file
    with open(FILENAME, 'wb') as file:
        packed_data = msgpack.packb(combined_data, use_bin_type=True)
        file.write(packed_data)

    return


if __name__ == '__main__':
    main()