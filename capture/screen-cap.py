import io
import time
import threading
import mss
from PIL import Image
from pynput import mouse, keyboard

# Lists to store actions
mouse_actions = []
keyboard_actions = []

# Mouse listener
def on_move(x, y):
    print('Pointer moved to {0}'.format((x, y)))
    mouse_actions.append(('move', x, y))

def on_click(x, y, button, pressed):
    print('{0} at {1}'.format('Pressed' if pressed else 'Released', (x, y)))
    if pressed:
        mouse_actions.append(('press', x, y, button))
    else:
        mouse_actions.append(('release', x, y, button))

def on_scroll(x, y, dx, dy):
    print('Scrolled {0} at {1}'.format('down' if dy < 0 else 'up',(x, y)))
    mouse_actions.append(('scroll', x, y, dx, dy))

# Keyboard listener
def on_key_press(key):
    try:
        print('alphanumeric key {0} pressed'.format(
            key.char))
    except AttributeError:
        print('special key {0} pressed'.format(
            key))
    keyboard_actions.append(('press', key))

def on_key_release(key):
    print('{0} released'.format(key))
    keyboard_actions.append(('release', key))

# Function to start mouse listener
def start_mouse_listener():
    with mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll) as listener:
        listener.join()

# Function to start keyboard listener
def start_keyboard_listener():
    with keyboard.Listener(on_press=on_key_press, on_release=on_key_release) as listener:
        listener.join()

# with mss.mss() as sct:
#     screenshot = sct.shot(output='screenshot.png')

TARGET_FPS = 30
DELAY = 1.0 / TARGET_FPS

def task():

    # Starting both listeners using threads
    mouse_thread = threading.Thread(target=start_mouse_listener)
    keyboard_thread = threading.Thread(target=start_keyboard_listener)

    mouse_thread.start()
    keyboard_thread.start()

    # Recording for a specified duration (e.g., 10 seconds for demonstration purposes)
    end_time = time.time() + 10

    while time.time() < end_time:
        time.sleep(1/30)  # 30 FPS

    # Stop the listeners
    for listener in [mouse_thread, keyboard_thread]:
        listener.join()

    print("Mouse actions:", mouse_actions)
    print("Keyboard actions:", keyboard_actions)

    with mss.mss() as sct:
        while True:
            start_time = time.time()
            
            for x in range(TARGET_FPS):
                screenshot = sct.grab({'mon': 1, 'top': 690, 'left': 750, 'width': 450, 'height': 50})

                # Save to the picture file
                # mss.tools.to_png(screenshot.rgb, screenshot.size, output='screenshot.png')

                # Convert to PIL from mss
                rgb = screenshot.rgb
                size = (screenshot.width, screenshot.height)
                pil_image = Image.frombytes('RGB', size, rgb)
                
                # Resize the image to 30% of the original size
                pil_image = pil_image.resize((int(pil_image.width * 0.3), int(pil_image.height * 0.3)), Image.ANTIALIAS)

                # Convert to byte array
                rgb_im = pil_image.convert('RGB')
                rgb_im = rgb_im.tobytes()

                # print(rgb_im)

                # Calculate remaining delay to maintain 30 fps
                elapsed_time = time.time() - start_time
                sleep_time = DELAY - elapsed_time
                if sleep_time > 0:
                    time.sleep(sleep_time)

            print(time.time() - start_time)

if __name__ == '__main__':
    task()
