import pygame
import msgpack
import io
from PIL import Image

# Constants
FILENAME = 'game_data_validate.mpk'
TARGET_FPS = 30
SCALE = 0.3
MAC_SCALE = 0.5

VISUAL_SCALE = 2

class InputType:
    MOUSE = 0
    KEYBOARD = 1

class KeyState:
    PRESS = 0
    RELEASE = 1
    MOVE = 2
    SCROLL = 3

EVENT_WINDOW_WIDTH = 300
EVENT_WINDOW_HEIGHT = 600
EVENT_LINE_HEIGHT = 40

def replay_with_visuals(filename):
    pygame.init()

    with open(filename, 'rb') as file:
        packed_data = file.read()
        data = msgpack.unpackb(packed_data, raw=False)

    frame_data = io.BytesIO(data[0]["frame"])
    img = Image.open(frame_data)
    img = img.convert("RGB")
    WIDTH, HEIGHT = int(img.size[0] / SCALE * MAC_SCALE * VISUAL_SCALE), int(img.size[1] / SCALE * MAC_SCALE * VISUAL_SCALE)

    combined_width = WIDTH + EVENT_WINDOW_WIDTH
    screen = pygame.display.set_mode((combined_width, max(HEIGHT, EVENT_WINDOW_HEIGHT)))
    pygame.display.set_caption('Replay')

    clock = pygame.time.Clock()

    pressed_keys = set()
    pressed_buttons = {}  # dict with button as key and (x, y) as value

    frame_count = 0  # Initialize frame counter outside of loop
    font_small = pygame.font.Font(None, 24)  # Font for the frame counter

    for entry in data:
        frame = Image.open(io.BytesIO(entry['frame']))
        frame = frame.convert("RGB")
        frame = frame.resize((WIDTH, HEIGHT), Image.LANCZOS)
        pygame_img = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
        screen.blit(pygame_img, (0, 0))

        pygame.draw.rect(screen, (0, 0, 0), (WIDTH, 0, EVENT_WINDOW_WIDTH, EVENT_WINDOW_HEIGHT))

        y_position = 10  # Start the y_position here

        # Visualize the currently pressed mouse buttons
        for button, (x, y) in pressed_buttons.items():
            pygame.draw.circle(screen, (255, 0, 0), (int(x * VISUAL_SCALE), int(y * VISUAL_SCALE)), 10)

        font = pygame.font.Font(None, 36)

        for event in entry['actions']:
            ts = event[0]
            input_type = event[1]
            state = event[2]

            if input_type == InputType.MOUSE:
                x, y = event[3], event[4]
                if state == KeyState.PRESS:
                    button_name = event[5]
                    pressed_buttons[button_name] = (x, y)
                    pygame.draw.circle(screen, (255, 0, 0), (int(x * VISUAL_SCALE), int(y * VISUAL_SCALE)), 10)
                elif state == KeyState.RELEASE:
                    button_name = event[5]
                    if button_name in pressed_buttons:
                        del pressed_buttons[button_name]

            elif input_type == InputType.KEYBOARD:
                key_char_or_name = event[3]
                if state == KeyState.PRESS:
                    pressed_keys.add(key_char_or_name)
                    # Render the key press visually here
                    key_text = font.render(key_char_or_name, True, (0, 255, 0))
                    screen.blit(key_text, (WIDTH + 10 + (EVENT_WINDOW_WIDTH - key_text.get_width() - 20) / 2, y_position))
                    y_position += EVENT_LINE_HEIGHT
                elif state == KeyState.RELEASE:
                    if key_char_or_name in pressed_keys:
                        pressed_keys.remove(key_char_or_name)

        # Increment and render frame counter
        counter_text = font_small.render(f"Frame: {frame_count}", True, (255, 255, 255))
        screen.blit(counter_text, (WIDTH - counter_text.get_width() - 10, HEIGHT - counter_text.get_height() - 10))

        pygame.display.flip()
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        clock.tick(TARGET_FPS)


    pygame.quit()

replay_with_visuals(FILENAME)
