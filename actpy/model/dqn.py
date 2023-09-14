import numpy as np
import random
from keras.models import Sequential
from keras.layers import Dense, Flatten, Conv2D, LeakyReLU
from keras.optimizers import Adam
from collections import deque

## ==================================================================
## Constants
## ==================================================================

GAMMA = 0.95 # discount rate
EPSILON = 1.0 # exploration rate
EPSILON_MIN = 0.01
EPSILON_DECAY = 0.995
LEARNING_RATE = 0.001

MEMORY_SIZE = 2000

CONVOLUTIONAL_LAYERS = [
    {
        "filters": 32,
        "kernel_size": (8, 8),
        "strides": (4, 4),
    },
    {
        "filters": 64,
        "kernel_size": (4, 4),
        "strides": (2, 2),
    },
    {
        "filters": 64,
        "kernel_size": (3, 3),
        "strides": (1, 1),
    },
]

DENSE_LAYERS = [
    {
        "units": 512,
    },
]


## ==================================================================
## DQN Class
## ==================================================================

class DQN:
    def __init__(self, frame_shape, action_size):
        self.frame_shape = frame_shape
        self.action_size = action_size
        self.memory = deque(maxlen=MEMORY_SIZE)
        self.gamma = GAMMA    
        self.epsilon = EPSILON
        self.epsilon_min = EPSILON_MIN
        self.epsilon_decay = EPSILON_DECAY
        self.learning_rate = LEARNING_RATE
        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()

    def _build_model(self):
        model = Sequential()
        
        # Add convolutional layers
        is_first_layer = True
        for layer in CONVOLUTIONAL_LAYERS:
            # First layer requires input shape, other convolutional layers infer it
            if is_first_layer:
                model.add(Conv2D(**layer, input_shape=self.frame_shape))
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
        model.add(Dense(self.action_size, activation='linear'))

        model.compile(loss='mse', optimizer=Adam(learning_rate=self.learning_rate))
        return model

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def predict(self, state):
        return self.model.predict(state)[0]

    def act(self, prediction):
        # Epsilon-greedy action selection
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        return np.argmax(prediction)

    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                # Use target_model for the Q-value prediction
                target = (reward + self.gamma * np.amax(self.target_model.predict(next_state)[0]))
            target_f = self.model.predict(state)
            target_f[0][action] = target
            self.model.train_on_batch(state, target_f)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def update_target_model(self):
        # Copy weights from model to target_model
        self.target_model.set_weights(self.model.get_weights())

    def load(self, name):
        self.model.load_weights(name)

    def save(self, name):
        self.model.save_weights(name)
