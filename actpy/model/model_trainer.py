import os
import random
import numpy as np
from collections import deque

from model.config import MEMORY_SIZE, BATCH_SIZE, GAMMA, UPDATE_TARGET_MODEL_EVERY, SAVE_WEIGHTS_EVERY
from model.nn import load_or_build_model

## ==================================================================
## Model Trainer Entry
## ==================================================================

def model_trainer_entry(stop_event, experience_queue, weights_queue):

    model = load_or_build_model()
    target_model = load_or_build_model()
    model.summary()

    memory = deque(maxlen=MEMORY_SIZE)
    train_count = 0

    while not stop_event.is_set():

        # Add all pending experiences to memory
        for _ in range(experience_queue.qsize()):
            prev_frames, prev_action_index, reward, frames_array, done = experience_queue.get()
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

            # Increment the frame count
            train_count += 1
            print(f"Trained {train_count} times")

            # Update the target model
            if train_count % UPDATE_TARGET_MODEL_EVERY == 0:
                # Copy weights from model to target_model
                target_model.set_weights(model.get_weights())

            # Sync weights with the model collector
            if train_count % SAVE_WEIGHTS_EVERY == 0:
                weights_queue.put(model.get_weights())
                model.save_weights(f"model_weights_{train_count}.h5")

