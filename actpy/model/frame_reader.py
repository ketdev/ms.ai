
import numpy as np
from struct import unpack
import zlib

from model.config import FRAME_WIDTH, FRAME_HEIGHT, FRAME_PACKET_HEADER_SIZE, MAX_PACKET_SIZE

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
        # float, float, float, uint64, uint64
        packet_header = packet[:FRAME_PACKET_HEADER_SIZE]
        hp, mp, exp, frame_number, length = unpack("fffQQ", packet_header)

        # Receive packet data
        packet_data = packet[FRAME_PACKET_HEADER_SIZE:]
        if len(packet_data) < length:
            raise Exception("Incomplete packet received")

        # decompress the packet data with zlib
        packet_data = zlib.decompress(packet_data)

        chunk8bit = _unpack_4bit_to_8bit(packet_data)
        frame = np.reshape(chunk8bit, (FRAME_HEIGHT, FRAME_WIDTH))

        frame_queue.put((addr, frame_number, frame, (hp, mp, exp)))

        # # update screen
        # _draw_grayscale_frame(screen, frame, 0, 0, FRAME_WIDTH * DISPLAY_SCALE, FRAME_HEIGHT * DISPLAY_SCALE)
        # _display_flip()
        

