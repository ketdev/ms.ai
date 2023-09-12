import io
import sys
import time
import mss
import numpy as np
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
## Screen Capture
## ==================================================================

# capture screenshots as a generator
def capture_screen(x, y, w, h):
    with mss.mss() as sct:
        while True:
            screenshot = sct.grab({"top": y, "left": x, "width": w, "height": h})

            # Convert to PIL from mss
            rgb = screenshot.rgb
            size = (screenshot.width, screenshot.height)
            pil_image = Image.frombytes('RGB', size, rgb)

            yield pil_image

## ==================================================================
## Image Utilities
## ==================================================================

def scale_image(image, scale):
    return image.resize((
        int(image.width * scale), 
        int(image.height * scale)
    ), Image.LANCZOS)

def grayscale_image(image):
    return image.convert('L')

def to_numpy_rgb(image):
    frame_width = image.width
    frame_height = image.height
    
    data = image.tobytes()
    data = np.frombuffer(data, dtype=np.uint8)
    data = np.reshape(data, (frame_height, frame_width, 3))
    data = np.transpose(data, (1, 0, 2))

    return data


def to_numpy_grayscale(image):
    frame_width = image.width
    frame_height = image.height
    
    data = image.tobytes()
    data = np.frombuffer(data, dtype=np.uint8)
    data = np.reshape(data, (frame_height, frame_width))
    data = np.transpose(data, (1, 0))

    return data