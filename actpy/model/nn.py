import os
import numpy as np
import random
from keras.models import Model
from keras.layers import Input, Concatenate, Dense, Flatten, Conv2D, LeakyReLU
from keras.optimizers import Adam
from collections import deque

from model.config import FRAME_HEIGHT, FRAME_WIDTH, FRAMES_PER_STEP, Actions, \
    MODEL_WEIGHTS_FILE, CONVOLUTIONAL_LAYERS, DENSE_LAYERS, LEARNING_RATE

## ==================================================================
## Methods
## ==================================================================

def load_or_build_model():
    model = build_model()
    if os.path.exists(MODEL_WEIGHTS_FILE):
        model.load_weights(MODEL_WEIGHTS_FILE)
    return model

def build_model():
     # Frame input and shape
    frame_input = Input(shape=(FRAME_HEIGHT, FRAME_WIDTH, FRAMES_PER_STEP))
    toggle_input = Input(shape=(Actions._SIZE,))

    x = frame_input

    # Convolutional layers for the frames
    for layer in CONVOLUTIONAL_LAYERS:
        x = Conv2D(**layer)(x)
        x = LeakyReLU()(x)

    x = Flatten()(x)

    # Concatenate flattened frames with toggle states
    x = Concatenate()([x, toggle_input])

    # Dense layers
    for layer in DENSE_LAYERS:
        x = Dense(**layer)(x)
        x = LeakyReLU()(x)

    # Output layer
    output = Dense(Actions._SIZE, activation='linear')(x)

    # Build and compile the model
    model = Model(inputs=[frame_input, toggle_input], outputs=output)
    model.compile(loss='mse', optimizer=Adam(learning_rate=LEARNING_RATE))
    return model

def epsilon_greedy_policy(prediction, epsilon=0):
    # Epsilon-greedy action selection
    if np.random.rand() <= epsilon:
        return random.randrange(Actions._SIZE)
    return np.argmax(prediction)
