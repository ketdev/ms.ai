from struct import pack

## ==================================================================
## Model Experience Dump Entry
## ==================================================================

def model_experience_dump_entry(stop_event, experience_queue):

    # Save all the experiences to a file
    with open("experiences.bin", "wb") as f:
        while not stop_event.is_set():

            # Get the next experience
            try:
                prev_frames, prev_action_index, reward, frames_array, done = experience_queue.get(timeout=1)
            except:
                continue

            # Save the experience to the file
            f.write(prev_frames)
            f.write(pack('i', prev_action_index))
            f.write(pack('f', reward))
            f.write(frames_array)
            f.write(pack('i', done))

    

        