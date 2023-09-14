
## ==================================================================
## Configurations
## ==================================================================

# Network
PORT = 12345

# Environment
FRAME_WIDTH = 512
FRAME_HEIGHT = 288
CAPTURE_TARGET_FPS = 24

# Packet Constants
FRAME_PACKET_HEADER_SIZE = 32
MAX_PACKET_SIZE = 65000 + FRAME_PACKET_HEADER_SIZE
MAX_KEYS = 6 
NO_KEY_VALUE = 0


## ==================================================================
## DQN Model Constants
## ==================================================================

MODEL_WEIGHTS_FILE = "model_weights.h5"
BATCH_SIZE = 32
UPDATE_TARGET_MODEL_EVERY = 1000
SAVE_WEIGHTS_EVERY = 5000

FRAMES_PER_STEP = 4


## ==================================================================
## Action space
## ==================================================================

class Actions:
    IDLE = 0
    ATTACK = 1
    JUMP = 2
    LEFT = 3
    RIGHT = 4
    DOWN = 5
    # UP = 6
    _SIZE = 6

# Action Virtual key codes
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
# Action Scan codes
KEY_JUMP = 0x1E # 'A'
KEY_ATTACK = 0x20 # 'D'

# Action Index -> IsVirtualKey, Key Code
ACTION_TO_KEY_MAP = {
    Actions.IDLE: (0, NO_KEY_VALUE),
    Actions.ATTACK: (0, KEY_ATTACK),
    Actions.JUMP: (0, KEY_JUMP),
    Actions.LEFT: (1, VK_LEFT),
    Actions.RIGHT: (1, VK_RIGHT),
    Actions.DOWN: (1, VK_DOWN),
    # Actions.UP: (1, VK_UP),
}

ACTION_NAMES = {
    Actions.IDLE: "IDLE",
    Actions.ATTACK: "ATTACK",
    Actions.JUMP: "JUMP",
    Actions.LEFT: "LEFT",
    Actions.RIGHT: "RIGHT",
    Actions.DOWN: "DOWN",
    # Actions.UP: "UP",
}

## ==================================================================
## Display
## ==================================================================

DISPLAY_SCALE = 2
BAR_HEIGHT = 20
BAR_TEXT_WIDTH = FRAME_WIDTH * DISPLAY_SCALE / 4
ACTIONS_TEXT_SIZE = 10
HP_COLOR = (245, 67, 114)
MP_COLOR = (6, 181, 223)
EXP_COLOR = (170, 204, 0)
ACTION_COLOR = (0, 37, 203)
ACTION_PICKED_COLOR = (173, 216, 230)