import pygame
import numpy as np

from model.config import FRAME_WIDTH, FRAME_HEIGHT, DISPLAY_SCALE, \
    BAR_HEIGHT, BAR_TEXT_WIDTH, ACTIONS_TEXT_SIZE, \
    HP_COLOR, MP_COLOR, EXP_COLOR, ACTION_COLOR, ACTION_PICKED_COLOR, \
    FRAMES_PER_STEP, Actions, ACTION_NAMES

## ==================================================================
## Display Logic with Pygame
## ==================================================================

def initialize_display():
    pygame.init()
    total_width = FRAME_WIDTH * DISPLAY_SCALE
    total_height = FRAME_HEIGHT * DISPLAY_SCALE * (1 + 1/4) + BAR_HEIGHT * 3 + 1 # margin
    screen = pygame.display.set_mode((total_width, total_height))
    pygame.display.set_caption('Captured Frames')
    return screen

def display_loop():
    while True:
        event = pygame.event.wait()
        if event.type == pygame.QUIT:
            break

def display_event_handle():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
    return False

def post_quit_event():
    pygame.event.post(pygame.event.Event(pygame.QUIT))

def close_display():
    pygame.quit()

def update_display(screen, frames, hp, mp, exp, action_states, action_vector, action_index):

    # clear the screen
    screen.fill((0, 0, 0))

    # draw the last four frames
    for i, f in enumerate(frames):
        # Set position and scale depending on the frame index
        if i == len(frames) - 1:  # last frame (most recent)
            h = FRAME_HEIGHT * DISPLAY_SCALE
            w = FRAME_WIDTH * DISPLAY_SCALE
            x = 0
            y = 0
        else:
            h = FRAME_HEIGHT * DISPLAY_SCALE / 4
            w = FRAME_WIDTH * DISPLAY_SCALE / 4 - 1
            x = (FRAMES_PER_STEP-i-2) * (w + 1) 
            y = FRAME_HEIGHT * DISPLAY_SCALE + 1 

        _draw_grayscale_frame(screen, f, x, y, w, h)

    # draw metrics
    bar_offset = FRAME_HEIGHT * DISPLAY_SCALE * (1+1/4) + 1
    bar_width = FRAME_WIDTH * DISPLAY_SCALE - BAR_TEXT_WIDTH - 1

    _draw_h_bar(screen, 0, bar_offset + 0 * BAR_HEIGHT + 1, bar_width, BAR_HEIGHT - 2, hp, HP_COLOR)
    _draw_h_bar(screen, 0, bar_offset + 1 * BAR_HEIGHT + 1, bar_width, BAR_HEIGHT - 2, mp, MP_COLOR)
    _draw_h_bar(screen, 0, bar_offset + 2 * BAR_HEIGHT + 1, bar_width, BAR_HEIGHT - 2, exp, EXP_COLOR)

    _draw_text(screen, "HP: {:.2f}%".format(hp*100), bar_width + 3, bar_offset + 0 * BAR_HEIGHT, BAR_HEIGHT - 2, HP_COLOR)
    _draw_text(screen, "MP: {:.2f}%".format(mp*100), bar_width + 3, bar_offset + 1 * BAR_HEIGHT, BAR_HEIGHT - 2, MP_COLOR)
    _draw_text(screen, "EXP: {:.2f}%".format(exp*100), bar_width + 3, bar_offset + 2 * BAR_HEIGHT, BAR_HEIGHT - 2, EXP_COLOR)

    # draw actions
    actions_text_size = ACTIONS_TEXT_SIZE
    actions_y_offset = FRAME_HEIGHT * DISPLAY_SCALE + 1
    actions_x_offset = FRAME_WIDTH * DISPLAY_SCALE - BAR_TEXT_WIDTH
    actions_height = FRAME_HEIGHT * DISPLAY_SCALE / 4 - 1

    # min-max normalize the action vector
    min_val, max_val = np.min(action_vector), np.max(action_vector)
    if min_val != 0 and max_val != 0:  # Avoid divide by zero
        probabilities = (action_vector - min_val) / (max_val - min_val)
    else:
        probabilities = action_vector
    # make sure the sum of the probabilities is 1
    prob_sum = np.sum(probabilities)
    if prob_sum > 0:
        probabilities /= prob_sum
    # make from 0.1 to 1
    probabilities = probabilities * 0.9 + 0.1

    for i in range(Actions._SIZE):
        action_width = BAR_TEXT_WIDTH / Actions._SIZE - 2
        action_height = actions_height - actions_text_size - 4
        action_x = actions_x_offset + i * (action_width + 2) + 1
        action_y = actions_y_offset + 1

        color = ACTION_COLOR 
        if action_index == i:
            color = ACTION_PICKED_COLOR

        _draw_v_bar(screen, action_x, action_y, action_width, action_height, probabilities[i], color)

        text_color = (255, 255, 255)
        if action_states[i] == 0:
            text_color = (100, 100, 100)

        _draw_text(screen, ACTION_NAMES[i], action_x, action_y + action_height + 1, actions_text_size, text_color)

    _display_flip()

## ==================================================================

def _draw_grayscale_frame(screen, frame, x, y, w, h):
    if frame is None:
        return
    # convert grayscale to rgb
    frame = np.stack([frame.swapaxes(0, 1)] * 3, -1)
    # convert frame to a surface from np array
    frame_surface = pygame.surfarray.make_surface(frame)
    # scale the frame to the display size
    frame_surface = pygame.transform.scale(frame_surface, (w, h))
    # draw the frame at the specified position
    screen.blit(frame_surface, (x, y))

def _draw_text(screen, text, x, y, size, color=(255, 255, 255)):
    font = pygame.font.SysFont("Arial", size)
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))

def _draw_h_bar(screen, x, y, w, h, percentage, color):
    bar_width = int(w * percentage)
    pygame.draw.rect(screen, color, (x, y, bar_width, h))

def _draw_v_bar(screen, x, y, w, h, percentage, color):
    bar_height = int(h * percentage)
    pygame.draw.rect(screen, color, (x, y + (h-bar_height), w, bar_height))

def _display_flip():
    pygame.display.flip()


## ==================================================================
## Display Entry
## ==================================================================

def display_entry(stop_event, display_queue):
    screen = initialize_display()

    while not stop_event.is_set():
        try:
            # get the next frame to display
            frames, (hp, mp, exp), action_states, action_vector, action_index = display_queue.get(timeout=0.1)
            # update the display
            update_display(screen, frames, hp, mp, exp, action_states, action_vector, action_index)

            # check for quit event
            display_event_handle()
        except:
            continue
            
    close_display()