#pragma once
#include <memory>

const int FRAME_WIDTH = 400; //640;
const int FRAME_HEIGHT = 225; //360;

const int NUMBER_OF_ROWS = 225;
const int CHUNK_SIZE = FRAME_WIDTH * NUMBER_OF_ROWS / 2; 

// Each byte has two 4-bit values

enum PacketType {
    METRICS,
    CHUNK
};

struct Metrics {
    float hp;
    float mp;
    float exp;
};

struct ChunkData {
    int index;
    unsigned char chunk_data[CHUNK_SIZE];
};

struct UDPPacket {
    PacketType type;
    union {
        Metrics header_data;
        ChunkData chunk_data;
    };
};