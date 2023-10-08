
# Make
mingw32-make



# Script

Let's make an AI learn how to play MapleStory

This was a really fun project that involved many different aspects and had quite some challenges.

For the AI to learn, i will be giving it:
    - screen captures, at 24 fps 4 frames at a time
        scaled down and in grayscale to save memory and model size
    - hp, mp, experience
    - minimap data (player position, portals)

After every 4 frames, it will answer with an action, from a list of possible actions it can do.

The reward will be calculated from the experience, hp and mp bars. Mostly experience as we want to level up as fast as possible.


# Architecture

My PC that runs MapleStory is not the best one, and training both the model and running the game is too heavy for it. So for that I'm going to train the model on a separate computer and send over the information on a local network port.

First i tried TCP, but it was too slow, I want near real-time so that the AI can perform the actions and have it affect the game, playing with lag makes it really hard even for a human.

Then i went for UDP, but the problem with UDP is the packet losses and out of order.