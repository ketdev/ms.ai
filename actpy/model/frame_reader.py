
import numpy as np
from struct import unpack
import zlib

from model.config import FRAME_WIDTH, FRAME_HEIGHT, FRAME_PACKET_HEADER_SIZE, MAX_PACKET_SIZE, \
    MAX_PORTALS, MAX_PRESSED_KEYS, NO_KEY_VALUE, Actions, KEY_TO_ACTION_MAP

## ==================================================================
## Utility Functions
## ==================================================================

def _unpack_4bit_to_8bit(packed_array):
    unpacked_size = 2 * len(packed_array)
    unpacked_array = np.zeros(unpacked_size, dtype=np.uint8)

    for i, val in enumerate(packed_array):
        # Extract the two 4-bit values from the packed byte
        pixel1 = (val & 0xF0) >> 4
        pixel2 = val & 0x0F

        # Convert the 4-bit values to 8-bit by repeating the same 4 bits
        unpacked_array[2*i] = pixel1 << 4
        unpacked_array[2*i + 1] = pixel2 << 4
        
    return unpacked_array

def _keys_to_actions(pressed_keys):
    actions = np.zeros(Actions._SIZE, dtype=np.uint8)
    for i, (isVirtualKey, isExtended, scanCode) in enumerate(pressed_keys):
        if scanCode == NO_KEY_VALUE:
            continue
        if scanCode in KEY_TO_ACTION_MAP:
            actions[KEY_TO_ACTION_MAP[scanCode]] = 1
        # else:
        #     print("Unknown key: {}".format(scanCode))
    return actions

## ==================================================================
## Frame Reader Entry
## ==================================================================

def frame_reader_entry(sock, stop_event, frame_queue):
    while not stop_event.is_set():

        # Receive packet header first
        packet, addr = sock.recvfrom(MAX_PACKET_SIZE)
        if len(packet) < FRAME_PACKET_HEADER_SIZE:
            raise Exception("Incomplete packet received")

        # Interpret header data
        # - Metrics: hp:float, mp:float, exp:float
        # - Minimap: width:uint16, height:uint16, playerX:uint16, playerY:uint16, portalX[MAX_PORTALS]:uint16, portalY[MAX_PORTALS]:uint16
        # - Frame number: frame_number:uint64
        # - Pressed keys: (isVirtualKey:uint8, isExtended:uint8, keyCode:uint8) x MAX_PRESSED_KEYS
        # - Packet length: length:uint64
        packet_header = packet[:FRAME_PACKET_HEADER_SIZE]
        hp, mp, exp = unpack("fff", packet_header[:12])
        minimap = unpack("HHHH" + "HH"*MAX_PORTALS, packet_header[12:20+MAX_PORTALS*4]) 
        # has 4 bytes padding to align to 8 bytes
        frame_number = unpack("Q", packet_header[24+MAX_PORTALS*4:32+MAX_PORTALS*4])[0]
        keys = packet_header[32+MAX_PORTALS*4:32+MAX_PORTALS*4+MAX_PRESSED_KEYS*3]
        length = unpack("Q", packet_header[-8:])[0]

        # Process minimap
        mapDim = (minimap[0], minimap[1])
        player = (minimap[2], minimap[3])
        portals = []        
        for i in range(MAX_PORTALS):
            portalX = minimap[4+i]
            portalY = minimap[4+i+MAX_PORTALS]
            if portalX != 65535 and portalY != 65535:
                portals.append((portalX, portalY))
        

        # Process pressed keys
        pressed_keys = []
        for i in range(MAX_PRESSED_KEYS):
            key = keys[i*3:i*3+3]
            isVirtualKey, isExtended, scanCode = unpack("BBB", key)
            if scanCode != NO_KEY_VALUE:
                pressed_keys.append((isVirtualKey, isExtended, scanCode))

        # translate actions to keys        
        action_state = _keys_to_actions(pressed_keys)

        # Receive packet data
        packet_data = packet[FRAME_PACKET_HEADER_SIZE:]
        if len(packet_data) < length:
            raise Exception("Incomplete packet received")

        # decompress the packet data with zlib
        packet_data = zlib.decompress(packet_data)

        chunk8bit = _unpack_4bit_to_8bit(packet_data)
        frame = np.reshape(chunk8bit, (FRAME_HEIGHT, FRAME_WIDTH))

        frame_queue.put((addr, frame_number, frame, (hp, mp, exp, mapDim, player, portals), action_state))

