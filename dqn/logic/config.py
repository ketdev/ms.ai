
## ==================================================================
## Configurations
## ==================================================================

# Network
SERVER_IP = '10.0.0.6'  # IP address of the training computer
PORT = 12345

# Environment
TARGET_WINDOW_NAME = "MapleStory"
MODEL_WEIGHTS_FILE = "model_weights.h5"
GRAYSCALE = True
FRAME_WIDTH = 640
FRAME_HEIGHT = 360

SCALE = 0.5

CAPTURE_TARGET_FPS = 20
FRAMES_PER_STEP = 4

# Window capture margins
WINDOW_MARGIN_LEFT = 8
WINDOW_MARGIN_TOP = 31
WINDOW_MARGIN_RIGHT = 8
WINDOW_MARGIN_BOTTOM = 8

# DQN Constants
BATCH_SIZE = 32
UPDATE_TARGET_MODEL_EVERY = 1000
SAVE_WEIGHTS_EVERY = 5000  # Save model weights every 5000 frames

# Action space
class Actions:
    IDLE = 0
    ATTACK = 1
    LEFT = 2
    RIGHT = 3
    # UP = 3
    # DOWN = 4
    # JUMP = 5
    _SIZE = 4

# Action Virtual key codes
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
# Action Scan codes
KEY_JUMP = 0x1E # 'A'
KEY_ATTACK = 0x20 # 'D'

ACTION_TO_KEY_MAP = {
    Actions.IDLE: None,
    Actions.ATTACK: KEY_ATTACK,
    Actions.LEFT: VK_LEFT,
    Actions.RIGHT: VK_RIGHT,
    # Actions.JUMP: KEY_JUMP,
    # Actions.UP: VK_UP,
    # Actions.DOWN: VK_DOWN,
}
