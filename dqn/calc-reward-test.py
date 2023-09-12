import sys
import threading
import time
from logic.metrics import get_metric_percentages, METRIC_DIMENSIONS
from capture.screen_capture import to_numpy_rgb
import numpy as np
import queue
import pygame
from PIL import Image

if __name__ == '__main__':

    # load image as example
    image = Image.open('./screenshot_crop.png')
    img_data = to_numpy_rgb(image)

    # get percentages
    percentages = get_metric_percentages(img_data)

    # Scale down by half
    # image = image.resize((int(image.width * 0.5), int(image.height * 0.5)), Image.LANCZOS)

    # show image on pygame
    pygame.init()
    screen = pygame.display.set_mode((image.width, image.height))
    pygame.display.set_caption('Captured Frames')
    # convert image to pygame surface
    frame_surface = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
    screen.blit(frame_surface, (0, 0))

    # draw lines where progress bars are
    for metric in METRIC_DIMENSIONS:
        left_margin = metric["left-margin"]
        right_margin = metric["right-margin"]
        bottom_margin = metric["bottom-margin"]       
        row_number = image.height - bottom_margin 
        width = image.width - left_margin - right_margin - 1
        pygame.draw.line(screen, (255, 0, 0), (left_margin, row_number), (left_margin + width, row_number), 1)

    pygame.display.flip()

    # wait for 5 seconds
    time.sleep(5)

    # quit pygame
    pygame.quit()