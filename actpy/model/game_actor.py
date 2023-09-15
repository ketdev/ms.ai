import numpy as np
import struct

from model.config import Actions, ACTION_TO_KEY_MAP, MAX_KEYS
    
## ==================================================================
## Utility Functions
## ==================================================================

def _send_action_packet(sock, addr, actions_toggle):
    # translate actions to keys
    keys = []
    for action_index, action in enumerate(actions_toggle):
        if action:
            keys.append(ACTION_TO_KEY_MAP[action_index])

    # Fill the rest of the packet with zeros (no keys)
    while len(keys) < MAX_KEYS:
        keys.append((0, 0))

    action_packet = b''.join(struct.pack('bb', key[0], key[1]) for key in keys)
    sock.sendto(action_packet, addr)


## ==================================================================
## Game Actor Entry
## ==================================================================

def game_actor_entry(sock, stop_event, action_queue):

    # Current actions toggle state
    actions_toggle = np.zeros(Actions._SIZE, dtype=np.uint8)

    while not stop_event.is_set():
        # Check if there is an action to be sent
        try:
            addr, action = action_queue.get(timeout=1)
        except:
            continue

        # Toggle actions
        actions_toggle[action] = not actions_toggle[action]

        # Movement actions are mutually exclusive (LEFT/RIGHT, UP/DOWN)
        if action == Actions.LEFT:
            actions_toggle[Actions.RIGHT] = False
        elif action == Actions.RIGHT:
            actions_toggle[Actions.LEFT] = False
        # if action == Actions.UP:
        #     actions_toggle[Actions.DOWN] = False
        # elif action == Actions.DOWN:
        #     actions_toggle[Actions.UP] = False

        # Send the action packet to the game
        _send_action_packet(sock, addr, actions_toggle)
