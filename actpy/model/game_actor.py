import numpy as np
import struct

from model.config import Actions, ACTION_TO_KEY_MAP, MAX_PRESSED_KEYS
    
## ==================================================================
## Utility Functions
## ==================================================================

def _actions_to_keys(action_states):
    # translate actions to keys
    keys = []
    for i, action in enumerate(action_states):
        if action == 1:
            keys.append(ACTION_TO_KEY_MAP[i])
    return keys

## ==================================================================
## Game Actor Entry
## ==================================================================

def game_actor_entry(sock, stop_event, action_queue):
    while not stop_event.is_set():
        # Check if there is an action to be sent
        try:
            addr, action_states = action_queue.get(timeout=1)
        except:
            continue

        # Translate actions to keys
        keys = _actions_to_keys(action_states)

        # Fill the rest of the packet with zeros (no keys)
        while len(keys) < MAX_PRESSED_KEYS:
            keys.append((0, 0, 0))

        # Send the action packet to the game
        action_packet = b''.join(struct.pack('bbb', key[0], key[1], key[2]) for key in keys)
        sock.sendto(action_packet, addr)

