import socket
import threading
from pynput import keyboard
from multiprocessing import Manager, Process

from model.config import PORT

## Processes and Threads
from model.debug_display import display_entry
from model.frame_reader import frame_reader_entry
from model.game_actor import game_actor_entry
from model.model_collector import model_collector_entry
from model.model_trainer import model_trainer_entry
from model.model_experience_dump import model_experience_dump_entry

## ==================================================================
## Keyboard Stop Condition (press ESC to stop)
## ==================================================================

def start_keyboard_listener(stop_event):
    def on_key_press(key):
        if key == keyboard.Key.esc:
            stop_event.set()
            # post_quit_event()
            return False
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()


## ==================================================================
## Main Processes
## ==================================================================

def main():
    # Initialize the socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PORT))

    # Initialize shared variables
    manager = Manager()
    stop_event = manager.Event() # signal to stop all threads and processes
    frame_queue = manager.Queue()
    action_queue = manager.Queue()
    display_queue = manager.Queue()
    experience_queue = manager.Queue()
    weights_queue = manager.Queue()

    # ------------------------------------------------------------------

    # Keyboard thread to stop the program
    keyboard_thread = threading.Thread(target=start_keyboard_listener, args=(stop_event,))
    keyboard_thread.start()

    # Frame reader collects frames from the game and puts them in the queue
    # - Updates the display with frames
    frame_reader = threading.Thread(target=frame_reader_entry, args=(s, stop_event, frame_queue))
    frame_reader.start()

    # Game actor takes actions from the queue and sends them to the game
    # - Updates the display with actions
    game_actor = threading.Thread(target=game_actor_entry, args=(s, stop_event, action_queue))
    game_actor.start()

    # Debug display
    display_process = Process(target=display_entry, args=(stop_event, display_queue))
    display_process.start()

    # Model collector processes the frames to get experience and puts actions in the queue
    # - Every now and then also updates the model weights from the trainer
    model_collector = Process(target=model_collector_entry, args=(
        stop_event, frame_queue, action_queue, experience_queue, weights_queue, display_queue))
    model_collector.start()

    # Model trainer updates the model weights from the collector, and signals the collector to update weights
    model_trainer = Process(target=model_trainer_entry, args=(stop_event, experience_queue, weights_queue))
    model_trainer.start()

    # # Model experience dump saves the experience to disk
    # model_trainer = Process(target=model_experience_dump_entry, args=(stop_event, experience_queue))
    # model_trainer.start()

    # ------------------------------------------------------------------

    # Wait for all to finish
    keyboard_thread.join()
    frame_reader.join()
    game_actor.join()
    display_process.join()
    model_collector.join()
    model_trainer.join()

    # Close the connection
    s.close()


if __name__ == '__main__':
    main()