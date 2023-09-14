#pragma once
#include <memory>

const int FRAME_WIDTH = 512; //640;
const int FRAME_HEIGHT = 288; //360;

const int MAX_BUFFER_SIZE = 65000;

// Each byte has two 4-bit values

struct Metrics {
    float hp;
    float mp;
    float exp;
};

struct UDPPacket {
    Metrics metrics;
    uint64_t frame_number;
    uint64_t length;
    unsigned char data[MAX_BUFFER_SIZE];
};

const int HEADER_SIZE = sizeof(UDPPacket) - MAX_BUFFER_SIZE;