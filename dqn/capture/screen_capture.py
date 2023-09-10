import io
import sys
import time
import threading
import queue
import mss
from PIL import Image
if sys.platform == "darwin":  # macOS
    from appscript import app
elif sys.platform == "win32":  # Windows
    import win32gui

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
## Screen Capture (Run in thread)
## ==================================================================


def screen_capture(x, y, w, h, fps, scale, grayscale, data_queue, stop_capture_func):    
    delay = 1.0 / fps
    with mss.mss() as sct:
        while not stop_capture_func():
            start_time = time.time()
            
            timestamp = time.time()
            screenshot = sct.grab({"top": y, "left": x, "width": w, "height": h})

            # Save to the picture file
            # mss.tools.to_png(screenshot.rgb, screenshot.size, output='screenshot.png')

            # Convert to PIL from mss
            rgb = screenshot.rgb
            size = (screenshot.width, screenshot.height)
            pil_image = Image.frombytes('RGB', size, rgb)
            
            # Resize the image to 30% of the original size
            pil_image = pil_image.resize((int(pil_image.width * scale), int(pil_image.height * scale)), Image.LANCZOS)
            
            # Convert to grayscale
            if grayscale:
                pil_image = pil_image.convert('L')
            else:
                pil_image = pil_image.convert('RGB')

            # # Convert to byte array
            # rgb_im = pil_image.tobytes()

            # Compress image using PNG
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            compressed_image_data = buffer.getvalue()

            # Put the image data into the queue as timestamp and image data tuple
            data_queue.put((timestamp, compressed_image_data))

            # Calculate remaining delay to maintain 30 fps
            elapsed_time = time.time() - start_time
            sleep_time = delay - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)
    return



# capture screenshots as a generator
def screen_capture_generator(x, y, w, h, scale, grayscale):
    with mss.mss() as sct:
        while True:
            screenshot = sct.grab({"top": y, "left": x, "width": w, "height": h})

            # Convert to PIL from mss
            rgb = screenshot.rgb
            size = (screenshot.width, screenshot.height)
            pil_image = Image.frombytes('RGB', size, rgb)
            
            # Detect display scaling
            display_scale_down = w / screenshot.width

            # Resize the image to a scale of the original size
            pil_image = pil_image.resize((
                int(pil_image.width * scale * display_scale_down), 
                int(pil_image.height * scale * display_scale_down)
            ), Image.LANCZOS)
            
            # Convert to grayscale
            if grayscale:
                pil_image = pil_image.convert('L')
            else:
                pil_image = pil_image.convert('RGB')

            # Convert to byte array
            rgb_im = pil_image.tobytes()

            # Return the image data
            yield rgb_im
    return