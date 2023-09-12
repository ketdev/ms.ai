import numpy as np

## ==================================================================
## Constants
## ==================================================================

# Metric dimensions to crop out of the screen
METRIC_DIMENSIONS = [
    {
        "name": "HP",
        "bottom-margin": 45,
        "left-margin": 527,
        "right-margin": 584,
        "color": "red",
    },
    {
        "name": "MP",
        "bottom-margin": 29,
        "left-margin": 527,
        "right-margin": 584,
        "color": "blue-green",
    },
    {
        "name": "EXP",
        "bottom-margin": 3,
        "left-margin": 15,
        "right-margin": 0,
        "color": "yellow-green",
    }
]

## ==================================================================
## Logic
## ==================================================================

def is_red(pixel):
    red, green, blue = pixel[:3]  # only take RGB, ignore alpha if it exists

    # Avoid division by zero
    if red == 0:
        return False

    # Check if the pixel is red-ish based on ratio
    blue_to_red_ratio = blue / red
    green_to_red_ratio = green / red

    # Check if pixel is light enough
    red_value = red / 255

    return blue_to_red_ratio < 0.7 and green_to_red_ratio < 0.7 and red_value > 0.5

def is_blue_green(pixel):
    red, green, blue = pixel[:3]  # only take RGB, ignore alpha if it exists

    # Avoid division by zero
    if blue == 0:
        return False

    # Check if the pixel is blue-ish based on ratio
    red_to_blue_ratio = red / blue

    # Check if pixel is light enough
    blue_value = blue / 255

    return red_to_blue_ratio < 0.7 and blue_value > 0.5

def is_yellow_green(pixel):
    red, green, blue = pixel[:3]  # only take RGB, ignore alpha if it exists

    # Avoid division by zero
    if green == 0:
        return False

    # Check if the pixel is yellow-green-ish based on ratio
    blue_to_green_ratio = blue / green

    # Check if pixel is light enough
    green_value = green / 255
    red_value = red / 255

    return blue_to_green_ratio < 0.7 and green_value > 0.7 and red_value > 0.5

def get_metric_percentages(img_data):
    frame_height = img_data.shape[1]
    frame_width = img_data.shape[0]

    percentages = {}

    for metric in METRIC_DIMENSIONS:
        left_margin = metric["left-margin"]
        right_margin = metric["right-margin"]
        bottom_margin = metric["bottom-margin"]
        color = metric["color"]

        # read progress bar from image
        row_number = frame_height - bottom_margin
        row = img_data[:, row_number, :]
        row = row[left_margin: frame_width - right_margin, :]

        if row.shape[0] == 0:
            percentages[metric["name"]] = 0
            continue

        # convert to boolean array by color
        if color == "red":
            row = np.apply_along_axis(is_red, 1, row)
        elif color == "blue-green":
            row = np.apply_along_axis(is_blue_green, 1, row)
        elif color == "yellow-green":
            row = np.apply_along_axis(is_yellow_green, 1, row)

        # Find first and last true values
        first_true = None
        last_true = None
        for i in range(row.shape[0]):
            if row[i]:
                if first_true is None:
                    first_true = i
                last_true = i

        # Calculate percentage
        if first_true is None or last_true is None:
            percentage = 0
        else:
            percentage = (last_true - first_true) / (row.shape[0] - 1)
            
        percentages[metric["name"]] = percentage
    
    return percentages
        
        