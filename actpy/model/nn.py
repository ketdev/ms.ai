import os
import numpy as np
import random
from keras.models import Model, Sequential
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

def load_or_build_model_from_old_weights():
    # Load old model
    model_old = build_old_model()
    model_old.summary()
    if os.path.exists(MODEL_WEIGHTS_FILE):
        model_old.load_weights(MODEL_WEIGHTS_FILE)

    # Build new model
    model = build_model()
    model.summary()

    # transfer layers from old model to new model
    new_layer_offset = 1  # +1 because the first layer in the new model is an InputLayer
    for i in [0, 2, 4]:
        model.layers[i + new_layer_offset].set_weights(model_old.layers[i].get_weights())

    return model

def build_old_model():
    state_shape = (FRAME_HEIGHT, FRAME_WIDTH, FRAMES_PER_STEP)

    model = Sequential()
    
    # Add convolutional layers
    is_first_layer = True
    for layer in CONVOLUTIONAL_LAYERS:
        # First layer requires input shape, other convolutional layers infer it
        if is_first_layer:
            model.add(Conv2D(**layer, input_shape=state_shape))
            is_first_layer = False
        else:
            model.add(Conv2D(**layer))
        model.add(LeakyReLU())

    # Flatten the output of the convolutional layers
    model.add(Flatten())
    
    # Fully connected layers
    for layer in DENSE_LAYERS:
        model.add(Dense(**layer))
        model.add(LeakyReLU())
    
    # add output layer
    model.add(Dense(Actions._SIZE, activation='linear'))

    model.compile(loss='mse', optimizer=Adam(learning_rate=LEARNING_RATE))
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
