#pragma once
#include <memory>
#include <set>

const int FRAME_WIDTH = 512; //640;
const int FRAME_HEIGHT = 288; //360;

const size_t MAX_PORTALS = 8;
const int MAX_BUFFER_SIZE = 65000;
const size_t MAX_PRESSED_KEYS = 16;
const char NO_KEY_VALUE = 0;

struct Metrics {
    float hp;
    float mp;
    float exp;
};

struct Minimap {
    uint16_t width, height;
    uint16_t playerX, playerY;
    uint16_t portalX[MAX_PORTALS], portalY[MAX_PORTALS];
};

struct KeyboardInput {
    uint8_t isVirtualKey;
    uint8_t isExtended; // Indicates if it's an extended key like 'Enter' or 'Alt'
    uint8_t keyCode;
    
    // Adding operators for std::set
    bool operator<(const KeyboardInput& other) const {
        return isVirtualKey < other.isVirtualKey 
            || isExtended < other.isExtended
            || keyCode < other.keyCode;
    }
    bool operator==(const KeyboardInput& other) const {
        return isVirtualKey == other.isVirtualKey 
            && isExtended == other.isExtended
            && keyCode == other.keyCode;
    }
};

// From client to server
struct FramePacket {
    Metrics metrics;
    Minimap minimap;
    uint64_t frameNumber;
    
    KeyboardInput pressedKeys[MAX_PRESSED_KEYS];

    // Compressed bytes, each byte has two 4-bit values
    uint64_t length;
    unsigned char data[MAX_BUFFER_SIZE];
};

const int FRAME_PACKET_HEADER_SIZE = sizeof(FramePacket) - MAX_BUFFER_SIZE;

// From server to client
struct ActionPacket {
    KeyboardInput pressedKeys[MAX_PRESSED_KEYS];
};
