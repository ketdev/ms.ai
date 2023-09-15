import os
import random
import numpy as np
from collections import deque
from struct import unpack, calcsize

from model.config import FRAME_WIDTH, FRAME_HEIGHT, FRAMES_PER_STEP
from model.config import MEMORY_SIZE, BATCH_SIZE, GAMMA, UPDATE_TARGET_MODEL_EVERY, SAVE_WEIGHTS_EVERY
from model.nn import load_or_build_model

EXPERIENCE_FILE = 'experiences.bin'

## ==================================================================
## Model Trainer Entry
## ==================================================================

def model_trainer_entry_from_file():

    model = load_or_build_model()
    target_model = load_or_build_model()
    memory = deque(maxlen=MEMORY_SIZE)
    frame_count = 0

    with open(EXPERIENCE_FILE, "rb") as f:
        while True:

            # Read the experience to the file
            prev_frames = f.read(FRAME_WIDTH * FRAME_HEIGHT * FRAMES_PER_STEP)
            if not prev_frames:
                break
            prev_action_index = unpack('i', f.read(calcsize('i')))[0]
            reward = unpack('f', f.read(calcsize('f')))[0]
            frames_array = f.read(FRAME_WIDTH * FRAME_HEIGHT * FRAMES_PER_STEP)
            done = unpack('i', f.read(calcsize('i')))[0]
            
            prev_frames = np.frombuffer(prev_frames, dtype=np.uint8).reshape((1, FRAME_HEIGHT, FRAME_WIDTH, FRAMES_PER_STEP))
            frames_array = np.frombuffer(frames_array, dtype=np.uint8).reshape((1, FRAME_HEIGHT, FRAME_WIDTH, FRAMES_PER_STEP))
    
            # Increment the frame count
            frame_count += 1

            # Add the experience to the memory
            memory.append((prev_frames, prev_action_index, reward, frames_array, done))

            # Check if we can replay
            if len(memory) > BATCH_SIZE:
                minibatch = random.sample(memory, BATCH_SIZE)
                for state, action, reward, next_state, done in minibatch:
                    target = reward
                    if not done:
                        # Use target_model for the Q-value prediction
                        target = (reward + GAMMA * np.amax(target_model.predict(next_state)[0]))
                    target_f = model.predict(state)
                    target_f[0][action] = target
                    model.train_on_batch(state, target_f)

            # Update the target model
            if frame_count % UPDATE_TARGET_MODEL_EVERY == 0:
                # Copy weights from model to target_model
                target_model.set_weights(model.get_weights())

            # Sync weights with the model collector
            if frame_count % SAVE_WEIGHTS_EVERY == 0:
                model.save_weights(f"model_weights_{frame_count}.h5")

if __name__ == '__main__':
    model_trainer_entry_from_file()
