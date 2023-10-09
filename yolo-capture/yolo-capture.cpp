#include <chrono>
#include <cstring>
#include <iostream>
#include <atomic>
#include <thread>
#include <string>
#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/opencv.hpp>

#include "../capp/screen-capture.hpp"


// ==================================================================
// Constants
// ==================================================================

// const char* const TARGET_WINDOW_NAME = "*Untitled - Notepad";
const char* const TARGET_WINDOW_NAME = "MapleStory";

const int CAPTURE_TARGET_FPS = 6;

// ==================================================================
// Global Variables
// ==================================================================

// Global stop flag
std::atomic<bool> stop_capture(false);

// ==================================================================
// Keyboard Stop Condition (press ESC to stop)
// ==================================================================

void start_keyboard_listener() {
    while (!stop_capture) {
        if (GetAsyncKeyState(VK_ESCAPE)) {
            stop_capture = true;
            exit(0);
            break;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

// ==================================================================
// Main Processes
// ==================================================================


int main() {
    try {
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

        std::thread keyboard_thread(start_keyboard_listener);
        ScreenCapturer capturer(x, y, w, h);

        // Preallocated buffers
        cv::Mat capturedImage;

        // FPS values
        int frameCount = 0;
        auto desiredFrameTime = std::chrono::milliseconds(static_cast<int>(1000 / CAPTURE_TARGET_FPS));
        auto busyWaitThreshold = std::chrono::milliseconds(10);  // Adjust as needed

        auto startTime = std::chrono::high_resolution_clock::now();
        while (!stop_capture) {
            auto frameStartTime = std::chrono::high_resolution_clock::now();
            frameCount++;

            // Capture frame
            capturer.capture(capturedImage);
            std::string filename = "frame_" + std::to_string(frameCount) + ".bmp";
            cv::imwrite(filename.c_str(), capturedImage);

            // Wait until next frame
            auto frameEndTime = std::chrono::high_resolution_clock::now();
            auto elapsedTime = std::chrono::duration_cast<std::chrono::milliseconds>(frameEndTime - frameStartTime);
            if (elapsedTime < desiredFrameTime) {
                std::this_thread::sleep_for(desiredFrameTime - elapsedTime  - busyWaitThreshold);
            }

            // Busy-wait loop
            while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - frameStartTime) < desiredFrameTime) {}
 
            // Report fps
            auto frameStep = frameCount % CAPTURE_TARGET_FPS;
            if (frameStep == 0) {
                double fps = static_cast<double>(CAPTURE_TARGET_FPS) / std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count();
                std::cout << "FPS: " << fps << std::endl;
                startTime = std::chrono::high_resolution_clock::now();
            }
        }

        keyboard_thread.join();

        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
    }
}
