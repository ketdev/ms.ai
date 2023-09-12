from multiprocessing import Process, Pipe, Value
import time
import threading
import numpy as np
from pynput import keyboard
from logic.config import CAPTURE_TARGET_FPS, FRAMES_PER_STEP, Actions
from logic.game_interface import init_game_interface, capture_frame, perform_action, display_info
from logic.model_interface import init_model_interface, reward_model, predict, replay_learning, model_stop

## ==================================================================
## Constants
## ==================================================================

FRAME_DELAY = 1.0 / CAPTURE_TARGET_FPS

## ==================================================================
## Global Variables
## ==================================================================

# Global stop flag
stop_capture = False

## ==================================================================
## Keyboard Stop Condition (press ESC to stop)
## ==================================================================

def start_keyboard_listener():
    def on_key_press(key):
        global stop_capture
        if key == keyboard.Key.esc:
            stop_capture = True
            return False
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()

## ==================================================================
## Main Processes
## ==================================================================

def game_interface_process(conn_game):

    # Start the keyboard listener thread
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.start()
    
    # Initialize the game interface
    init_game_interface()

    # Initialize the frame buffer
    frame_data, metrics = next(capture_frame()) # dummy frame for dimensions
    frames = np.zeros((frame_data.shape[0], frame_data.shape[1], FRAMES_PER_STEP), dtype=np.uint8)
    metrics_buffer = []
    action_vector = np.zeros(Actions._SIZE, dtype=np.float32)
    action = Actions.IDLE

    # Send dimensions to the prediction process
    conn_game.send(frames.shape)

    # Keep track of frames per second
    frame_count = 0
    fps_start_time = time.time()
    fps = 0

    # Start the prediction process
    while not stop_capture:
        timestamp = time.time()

        # Capture the frames and send it
        frame_data, metrics = next(capture_frame())

        # Accumulate frames and metrics
        frames = np.roll(frames, -1, axis=2)
        frames[:, :, -1] = frame_data
        metrics_buffer.append(metrics)
        
        # Update frames per second
        frame_count += 1
        if time.time() - fps_start_time >= 1:
            fps = frame_count
            frame_count = 0
            fps_start_time = time.time()

        # Send frames to the prediction process
        if frame_count % FRAMES_PER_STEP == 0:
            # Send all frames to the prediction process
            conn_game.send((frames, metrics_buffer))

            # Wait for the prediction to return
            action_vector, action = conn_game.recv()

            # Perform action in game environment
            perform_action(action_vector, action)

            # Reset frame buffer
            metrics_buffer = []

        # Display the frames and metrics
        display_info(frames, metrics_buffer, action_vector, action, fps)

        # Calculate remaining delay to maintain target FPS
        elapsed_time = time.time() - timestamp
        sleep_time = FRAME_DELAY - elapsed_time
        if sleep_time > 0:
            time.sleep(sleep_time)
    
    # Send the stop signal to the prediction process
    conn_game.send((None, None))

    # Close the connection
    conn_game.close()

    # Join the keyboard listener thread
    keyboard_thread.join()

def model_interface_process(conn_model):

    # Receive dimensions from the game process
    frames_shape = conn_model.recv()

    # Initialize the model interface
    init_model_interface(frames_shape)

    # Initialize the agent
    frame_count = 0
    prev_frames = None
    prev_action = None

    # Start the prediction process
    stopping = False
    while not stopping:
        # Get frames from the connection
        next_frames, metrics_list = conn_model.recv()
        if next_frames is None:
            stopping = True
            break

        # Reward the model
        reward_model(prev_frames, prev_action, metrics_list, next_frames)

        # Process the frames and predict the action
        action_vector, action = predict(next_frames)
        conn_model.send((action_vector, action))

        # Update the agent
        prev_frames = next_frames
        prev_action = action

        # Update frame count
        frame_count += 1

        # Replay learning
        replay_learning(frame_count)

    # Close the connection
    conn_model.close()

    # Stop the model
    model_stop()

## ==================================================================
## Main
## ==================================================================

if __name__ == '__main__':
    
    conn_game, conn_model = Pipe()
    
    p1 = Process(target=game_interface_process, args=(conn_game,))
    p2 = Process(target=model_interface_process, args=(conn_model,))
    
    p1.start()
    p2.start()
    
    p1.join()
    p2.join()

    # Close the main ends of the pipes
    conn_game.close()
    conn_model.close()

    print("Done!")
