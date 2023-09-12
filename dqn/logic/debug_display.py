import pygame
import numpy as np

## ==================================================================
## Constants
## ==================================================================

DISPLAY_SCALE = 2
FRAMES_PER_STEP = 4
DISPLAY_METRIC_BAR_HEIGHT = 20 
DISPLAY_ACTION_PROB_HEIGHT = 100

## ==================================================================
## Display Logic with Pygame
## ==================================================================

def initialize_display(width, height):
    pygame.init()
    total_width = width * DISPLAY_SCALE
    total_height = height * DISPLAY_SCALE + DISPLAY_METRIC_BAR_HEIGHT * 3 + DISPLAY_ACTION_PROB_HEIGHT
    screen = pygame.display.set_mode((total_width, total_height))
    pygame.display.set_caption('Captured Frames')
    return screen

def draw_metric_bars(screen, metrics, y_offset):
    """Draw the HP, MP, and EXP bars."""
    for name in ["HP", "MP", "EXP"]:
        percentage = metrics[name]
        bar_width = int(screen.get_width() * percentage)
        color = (255, 0, 0) if name == "HP" else (0, 0, 255) if name == "MP" else (255, 255, 0)
        pygame.draw.rect(screen, color, (0, y_offset + 1, bar_width, DISPLAY_METRIC_BAR_HEIGHT - 2))
        y_offset += DISPLAY_METRIC_BAR_HEIGHT

def draw_action_probabilities(screen, act_vector, action_taken, y):
    """Draw action probabilities as vertical bars."""
    # min-max normalize the action vector
    min_val, max_val = np.min(act_vector), np.max(act_vector)
    if max_val - min_val != 0:  # Avoid divide by zero
        probabilities = (act_vector - min_val) / (max_val - min_val)
    else:
        probabilities = act_vector
    # make sure the sum of the probabilities is 1
    prob_sum = np.sum(probabilities)
    probabilities /= prob_sum if prob_sum != 0 else 1

    bar_width = screen.get_width() // len(probabilities)
    for index, prob in enumerate(probabilities):
        color = (0, 0, 255)  # Blue color for all actions
        if index == action_taken:
            color = (173, 216, 230)  # Light blue for taken action
        height = int(DISPLAY_ACTION_PROB_HEIGHT * prob)
        pygame.draw.rect(screen, color, 
            (index * bar_width, y + DISPLAY_ACTION_PROB_HEIGHT - height, bar_width, height))

def display_frames(screen, frames, metrics, act_vector, action_taken, fps):
    frame_height = frames.shape[1] * DISPLAY_SCALE
    frame_width = frames.shape[0] * DISPLAY_SCALE

    # clear the screen
    screen.fill((0, 0, 0))

    # Transpose and enumerate the frames
    for i, frame in enumerate(frames.transpose(2, 0, 1)):
        inv = FRAMES_PER_STEP - i - 1
        frame = np.stack([frame] * 3, -1)
        frame_surface = pygame.surfarray.make_surface(frame)
        if inv == 0:
            # scale the first frame
            frame_surface = pygame.transform.scale(frame_surface, (frame_width, frame_height))
            # draw the first frame in the top left corner
            screen.blit(frame_surface, (0, 0))
            continue
        else:
            # scale the frame by 1/3 to make it smaller
            frame_surface = pygame.transform.scale(frame_surface, (frame_width // 3, frame_height // 3))
            # draw to the right of first frame, top to bottom
            screen.blit(frame_surface, (frame_width, (inv - 1) * frame_height // 3))
    
    # Draw metric bars for last frame
    if len(metrics) > 0:
        last_metrics = metrics[-1]
        draw_metric_bars(screen, last_metrics, frame_height)
    
    # Draw action probabilities
    draw_action_probabilities(screen, act_vector, action_taken, frame_height + DISPLAY_METRIC_BAR_HEIGHT * 3)
 
    # Show FPS at top right corner
    font = pygame.font.SysFont("Arial", 20)
    fps_text = "FPS:" + str(fps)
    fps_surface = font.render(fps_text, True, (0, 255, 0))
    screen.blit(fps_surface, (screen.get_width() - fps_surface.get_width(), 0))

    pygame.display.flip()

def display_event_loop():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
    return False

def close_display():
    pygame.quit()
