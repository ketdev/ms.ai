import numpy as np
from collections import deque

from model.config import FRAMES_PER_STEP, Actions, EPSILON, EPSILON_DECAY, EPSILON_MIN
from model.nn import load_or_build_model, epsilon_greedy_policy

## ==================================================================
## Utilities
## ==================================================================

def _get_reward(prev_metrics, prev_action_index, next_metrics):
    if prev_metrics is None:
        return 0

    prev_hp, prev_mp, prev_exp = prev_metrics
    next_hp, next_mp, next_exp = next_metrics

    # Reward when experience bar increases
    exp_reward = (next_exp - prev_exp) * 100
    exp_reward = max(exp_reward, 0)

    # Punish when health bar decreases
    damage_punish = (prev_hp - next_hp) * 10
    damage_punish = max(damage_punish, 0)
    
    # Punish slightly when mana bar decreases
    mana_save_punish = (prev_mp - next_mp) * 1
    mana_save_punish = max(mana_save_punish, 0)

    # Punish slightly for unnecessary actions
    action_punish = 0 if prev_action_index == Actions.IDLE else 0.001

    return exp_reward - damage_punish - mana_save_punish - action_punish


## ==================================================================
## Model Collector Entry
## ==================================================================

def model_collector_entry(stop_event, frame_queue, action_queue, experience_queue, weights_queue, display_queue):
    
    model = load_or_build_model()

    # Initialize counters
    frame_step = 0
    frame_count = 0
    frames = deque(maxlen=FRAMES_PER_STEP)

    action_vector = np.zeros(Actions._SIZE, dtype=np.float32)
    action_index = 0 # picked action index
    reward = 0

    prev_frames = None
    prev_action_index = None
    prev_metrics = None

    epsilon = EPSILON

    while not stop_event.is_set():

        # Get the next frame
        try:
            addr, frame_number, frame, metrics = frame_queue.get(timeout=1)
        except:
            continue

        # accumulate data
        frames.append(frame)
        frame_step += 1
        reward += _get_reward(prev_metrics, prev_action_index, metrics)
        prev_metrics = metrics

        # Send data to update display
        display_queue.put((frames, metrics, action_vector, action_index))

        if frame_step >= FRAMES_PER_STEP:

            # turn frames to numpy array
            frames_array = np.array(frames, dtype=np.uint8)   
            frames_array = np.transpose(frames_array, (1, 2, 0))
            frames_array = np.reshape(frames_array, [1, frames_array.shape[0], frames_array.shape[1], frames_array.shape[2]])

            # Reward the model for previous action
            if reward != 0:
                print(f"REWARD: {reward}")

            # Collect experience
            if prev_frames is not None:                
                experience_queue.put((prev_frames, prev_action_index, reward, frames_array, False))

            # Get action from DQN agent
            action_vector = model.predict(frames_array)[0]
            action_index = epsilon_greedy_policy(action_vector, epsilon)            
            if epsilon > EPSILON_MIN:
                epsilon *= EPSILON_DECAY
            else:
                print("=== EPSILON MIN REACHED ===")
            
            # Queue action for the game
            action_queue.put((addr, action_index))

            # Update counters
            prev_frames = frames_array
            prev_action_index = action_index
            frame_count += 1
            frame_step = 0
            reward = 0

            # Check if we need to synchronize weights
            if weights_queue.qsize() > 0:
                sync_weights = weights_queue.get()
                model.set_weights(sync_weights)
                epsilon = EPSILON

