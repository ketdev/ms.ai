#include <iostream>
#include <thread>
#include <chrono>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <cstring>

#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")  // Link with ws2_32.lib

#include "screen-capture.hpp"

// ==================================================================
// Constants
// ==================================================================

const float FRAME_DELAY = 1.0f / CAPTURE_TARGET_FPS;
const int FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT;

// ==================================================================
// Global Variables
// ==================================================================

// Global stop flag
bool stop_capture = false;

// Add other constants and configurations as needed.

// ==================================================================
// Helper functions
// ==================================================================

void initialize_winsock() {
    WSADATA wsaData;
    int iResult = WSAStartup(MAKEWORD(2,2), &wsaData);
    if (iResult != 0) {
        std::cerr << "WSAStartup failed: " << iResult << "\n";
        exit(1);
    }
}

void cleanup_winsock() {
    WSACleanup();
}


// ==================================================================
// Keyboard Stop Condition (press ESC to stop)
// ==================================================================

void start_keyboard_listener() {
    char c;
    while (!stop_capture) {
        std::cin >> c;
        if (c == 27) { // ESC key
            stop_capture = true;
            break;
        }
    }
}

// ==================================================================
// Main Processes
// ==================================================================

void send_loop(int sock, int x, int y, int w, int h) {
    ScreenCapturer capturer(x, y, w, h);

    while (streamingCondition) {
        cv::Mat frame = capturer.capture(x, y);
        // Process and send the frame as needed
    }
}

// void send_data(int sock, const std::map<std::string, float>& metrics, const cv::Mat& frame) {
//     // Serialize metrics and frame to send over the socket.
//     // Use OpenCV methods to convert the image to bytes, and struct to pack metrics.
// }

void recv_loop(int sock) {
    // Similar logic, with modifications to use C++ libraries.
}

int main() {

    // Initialize Winsock
    initialize_winsock();

    // Create a socket
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in serv_addr;
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);
    inet_pton(AF_INET, SERVER_IP, &serv_addr.sin_addr);

    connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr));
    
    // Use appropriate C++ methods to get window bounds.
    // E.g., using Xlib for Linux.
    
    std::thread keyboard_thread(start_keyboard_listener);
    std::thread send_thread(send_loop, sock, x, y, w, h);
    std::thread recv_thread(recv_loop, sock);
    
    keyboard_thread.join();
    send_thread.join();
    recv_thread.join();

    close(sock);
    
    // Cleanup Winsock
    cleanup_winsock();

    return 0;
}
