import os
import threading
import numpy as np

from model.dqn import DQN
from logic.config import MODEL_WEIGHTS_FILE, Actions, \
    BATCH_SIZE, UPDATE_TARGET_MODEL_EVERY, SAVE_WEIGHTS_EVERY 
    

## ==================================================================
## Global Variables
## ==================================================================

# Agent 
agent = None

# Last processed frame metrics
last_metrics = None

# Global event for replay
can_replay = threading.Event()

# Stop flag
stop_training = False

# Training thread
training_thread = None


## ==================================================================

def init_model_interface(state_shape):
    global agent

    # Initialize DQN agent
    agent = DQN(state_shape, Actions._SIZE)
    agent.model.summary()

    # Load model weights if exists
    if os.path.exists(MODEL_WEIGHTS_FILE):
        agent.load(MODEL_WEIGHTS_FILE)

    # Start the agent training thread
    training_thread = threading.Thread(target=_train_agent)
    training_thread.start()


def reward_model(prev_frames, prev_action, metrics_list, next_frames):
    done = False
    global last_metrics

    # Accumulate reward for each frame
    reward = 0
    for metrics in metrics_list:
        reward += _get_reward(last_metrics, metrics)
        last_metrics = metrics
    
    if reward > 0:
        print(f"REWARD: {reward}")

    # Reshape frames to 1 frame set of 4 frames
    if prev_frames is not None:
        prev_frames = np.reshape(prev_frames, [1, prev_frames.shape[0], prev_frames.shape[1], prev_frames.shape[2]])
        next_frames = np.reshape(next_frames, [1, next_frames.shape[0], next_frames.shape[1], next_frames.shape[2]])

        # Store previous state, action, reward, next_state, done in agent memory
        agent.remember(prev_frames, prev_action, reward, next_frames, done)


def predict(frames):
    # Reshape frames to 1 frame set of 4 frames
    frames = np.reshape(frames, [1, frames.shape[0], frames.shape[1], frames.shape[2]])

    # Get action from DQN agent
    action_vector = agent.predict(frames)
    action = agent.act(action_vector)
    return action_vector, action

def replay_learning(frame_count):
    # Check if the agent can replay
    if len(agent.memory) > BATCH_SIZE:
        can_replay.set()  # Signal to the training thread that it can start a replay

    if frame_count % UPDATE_TARGET_MODEL_EVERY == 0:
        agent.update_target_model()

    if frame_count % SAVE_WEIGHTS_EVERY == 0:
        agent.save(f"dqn_weights_{frame_count}.h5")  # save with the frame count for clarity

def model_stop():
    global stop_training
    stop_training = True
    training_thread.join()


## ==================================================================
## Internal Functions
## ==================================================================

def _get_reward(prev_metrics, next_metrics):
    if prev_metrics is None:
        return 0

    # Reward when experience bar increases
    prev_experience = prev_metrics["EXP"]
    new_experience = next_metrics["EXP"]
    exp_reward = (new_experience - prev_experience) * 100
    exp_reward = max(exp_reward, 0)
    # Punish when health bar decreases
    prev_health = prev_metrics["HP"]
    new_health = next_metrics["HP"]
    damage_punish = (prev_health - new_health) * 10
    damage_punish = max(damage_punish, 0)
    
    return exp_reward - damage_punish

def _train_agent():
    while not stop_training:
        can_replay.wait()  # Wait until main loop signals a replay is possible
        if len(agent.memory) > BATCH_SIZE:
            agent.replay(BATCH_SIZE)
            can_replay.clear()  # Reset the event flag
