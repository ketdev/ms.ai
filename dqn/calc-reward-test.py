import sys
import threading
import time
import numpy as np
import queue
import pygame
from PIL import Image

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


if __name__ == '__main__':

    # load image as example
    image = Image.open('./dqn/screen-test.png')

    # Scale down by half
    image = image.resize((int(image.width * 0.5), int(image.height * 0.5)), Image.LANCZOS)

    # Convert bytes to numpy array
    frame_width = image.width
    frame_height = image.height
    
    # convert to pixels
    data = image.tobytes()

    # transpose image bytes to same format for make_surface
    data = np.frombuffer(data, dtype=np.uint8)
    data = np.reshape(data, (frame_height, frame_width, 4))
    data = np.transpose(data, (1, 0, 2))
    # remove alpha channel
    data = data[:, :, :3]

    # read progress bar from image (row 4 from bottom)
    row_number = frame_height - 3
    row = data[:, row_number, :]

    # turn yellow pixels into white and everything else into black
    first_yellow = None
    last_continuous_yellow = None
    exp_bar = np.zeros((row.shape[0], 3), dtype=np.uint8)
    for i in range(row.shape[0]):
        if is_yellow_green(row[i]):
            if first_yellow is None:
                first_yellow = i
            last_yellow = i
            exp_bar[i] = (255, 255, 255)
        else:
            exp_bar[i] = (0, 0, 0)

    # calculate exp bar percentage
    exp_bar_percentage = (last_yellow - first_yellow) / (row.shape[0] - first_yellow)
    print("exp bar percentage: ", exp_bar_percentage * 100)

    # show image on pygame
    pygame.init()
    screen = pygame.display.set_mode((image.width, image.height))
    pygame.display.set_caption('Captured Frames')
    frame_surface = pygame.surfarray.make_surface(data)
    screen.blit(frame_surface, (0, 0))

    # draw line where progress bar is
    pygame.draw.line(screen, (255, 0, 0), (0, row_number), (frame_width, row_number), 1)

    # draw progress bar pixels blown up 40 in height
    for i in range(row.shape[0]):
        color_value = row[i]
        pygame.draw.line(screen, color_value, (i, 0), (i, 80), 1)

    # draw exp bar pixels blown up 40 in height under progress bar
    for i in range(exp_bar.shape[0]):
        color_value = exp_bar[i]
        pygame.draw.line(screen, color_value, (i, 80), (i, 160), 1)

    pygame.display.flip()

    # wait for 5 seconds
    time.sleep(5)

    # quit pygame
    pygame.quit()