#include <iostream>
#include <thread>
#include <chrono>
#include <cstring>
#include "CImg.h"

#include "network.hpp"
#include "screen-capture.hpp"
#include "metrics.hpp"
#include "input.hpp"


// ==================================================================
// Constants
// ==================================================================

const char* const SERVER_IP = "10.0.0.6"; // IP address of the training computer
const int PORT = 12345;

const char* const TARGET_WINDOW_NAME = "Untitled - Notepad";
const int FRAME_WIDTH = 640;
const int FRAME_HEIGHT = 360;
const int CAPTURE_TARGET_FPS = 30;
const int FRAMES_PER_STEP = 4;

const float FRAME_DELAY = 1.0f / CAPTURE_TARGET_FPS;
const int FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT;

// ==================================================================
// Global Variables
// ==================================================================

// Global stop flag
bool stop_capture = false;


// ==================================================================
// Keyboard Stop Condition (press ESC to stop)
// ==================================================================

void start_keyboard_listener() {
    while (!stop_capture) {
        if (GetAsyncKeyState(VK_ESCAPE)) {
            stop_capture = true;
            break;
        }
        Sleep(100);  // don't hog the CPU
    }
}


// ==================================================================
// Utilities
// ==================================================================

cimg_library::CImg<unsigned char> convertToCImg(const std::vector<BYTE>& bytes, int width, int height) {
    DWORD dwStride = ((width * 32 + 31) / 32) * 4;
    cimg_library::CImg<unsigned char> img(width, height, 1, 4);
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            int byteIndex = y * dwStride + x * 4;
            for (int c = 0; c < 4; c++) {
                img(x, y, 0, c) = bytes[byteIndex + c];
            }
        }
    }
    return img;
}


// ==================================================================
// Main Processes
// ==================================================================

void send_loop(int sock, int x, int y, int w, int h) {
    ScreenCapturer capturer(x, y, w, h);
    int frameCount = 0;
    auto startTime = std::chrono::high_resolution_clock::now();

    while (!stop_capture) {
        frameCount++;

        std::vector<BYTE> bytes = capturer.capture_bytes();
        cimg_library::CImg<unsigned char> image = convertToCImg(bytes, w, h);
        Metrics metrics = get_metric_percentages(image, w, h);

        // // Resize the image
        // image.resize(FRAME_WIDTH, FRAME_HEIGHT, -100, -100, 3);
        
        // Convert BGRA to Grayscale
        cimg_library::CImg<unsigned char> grayscale(FRAME_WIDTH, FRAME_HEIGHT, 1, 1, 0);
        cimg_forXY(grayscale, x, y) {
            unsigned char r = image(x, y, 0);
            unsigned char g = image(x, y, 1);
            unsigned char b = image(x, y, 2);
            unsigned char gray = static_cast<unsigned char>(0.299f * r + 0.587f * g + 0.114f * b);
            grayscale(x, y) = gray;
        }

        // // Display the image
        // cimg_library::CImgDisplay display(grayscale, "Display window");
        // while (!display.is_closed()) {
        //     display.wait();
        //     if (display.is_keyESC()) break;
        // }

        // send metrics in socket
        send(sock, (char*)&metrics, sizeof(metrics), 0);

        // send bytes in socket
        int frame_bytes = grayscale.width() * grayscale.height();
        send(sock, (char*)grayscale.data(), frame_bytes, 0);

        // Report fps
        auto currentTime = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsedSeconds = currentTime - startTime;
        if (elapsedSeconds.count() >= 1.0) { // Check every second
            double fps = frameCount / elapsedSeconds.count();
            std::cout << "FPS: " << fps << std::endl;

            frameCount = 0;
            startTime = std::chrono::high_resolution_clock::now();
        }
    }
}


void recv_loop(int sock) {
    int frame_step = 0;
    while (!stop_capture) {
        frame_step += 1;
        if (frame_step >= FRAMES_PER_STEP) {
            frame_step = 0;
            uint8_t action = 0;
            recv(sock, (char*)&action, 1, 0);
            std::cout << "Action: " << action << std::endl;
        }
    }
}

int main() {

    HWND hwnd = FindWindowA(NULL, TARGET_WINDOW_NAME);
    if (hwnd != NULL) {
        std::cout << "Window found!" << std::endl;
    } else {
        std::cout << "Window not found!" << std::endl;
    }

    auto rect = ScreenCapturer::GetClientRectangle(TARGET_WINDOW_NAME);
    int x = rect.left;
    int y = rect.top;
    int w = rect.right - rect.left;
    int h = rect.bottom - rect.top;

    std::cout << x << std::endl;
    std::cout << y << std::endl;
    std::cout << w << std::endl;
    std::cout << h << std::endl;

    // Initialize Winsock
    initialize_winsock();

    // Create a socket
    SOCKET sock = create_socket();

    // Connect to server
    connect_to_server(sock, SERVER_IP, PORT);
        
    std::thread keyboard_thread(start_keyboard_listener);
    std::thread send_thread(send_loop, sock, x, y, w, h);
    std::thread recv_thread(recv_loop, sock);
    
    keyboard_thread.join();
    send_thread.join();
    recv_thread.join();

    // Close the socket
    close_socket(sock);
    
    // Cleanup Winsock
    cleanup_winsock();

    return 0;
}
