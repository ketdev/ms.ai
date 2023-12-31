#include <chrono>
#include <cstring>
#include <iostream>
#include <atomic>
#include <thread>
#include <zlib.h>
#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/opencv.hpp>

#include "network.hpp"
#include "input.hpp"
#include "metrics.hpp"
#include "minimap.hpp"
#include "protocol.hpp"
#include "screen-capture.hpp"
#include "compress.hpp"


// ==================================================================
// Constants
// ==================================================================

const char* const SERVER_IP = "10.0.0.7";
const int PORT = 12345;

// const char* const TARGET_WINDOW_NAME = "*Untitled - Notepad";
const char* const TARGET_WINDOW_NAME = "MapleStory";

const int CAPTURE_TARGET_FPS = 24;

// ==================================================================
// Global Variables
// ==================================================================

// Global stop flag
std::atomic<bool> stop_capture(false);

// Global state to hold key presses
std::set<KeyboardInput> pressedKeys;

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
// Keyboard Low Level Hook
// ==================================================================

LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        KBDLLHOOKSTRUCT* kb = (KBDLLHOOKSTRUCT*)lParam;

        // Capture virtual keys
        KeyboardInput key;
        key.isExtended = (kb->flags & LLKHF_EXTENDED) != 0;
        key.keyCode = static_cast<uint8_t>(kb->vkCode); // for virtual keys

        if (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN) {
            key.isVirtualKey = 1;
            pressedKeys.insert(key);
        } else if (wParam == WM_KEYUP || wParam == WM_SYSKEYUP) {
            key.isVirtualKey = 1;
            pressedKeys.erase(key);
        }

        // For scan codes, we can do similar but with:
        key.keyCode = static_cast<uint8_t>(kb->scanCode); 
        key.isVirtualKey = 0;

        if (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN) {
            pressedKeys.insert(key);
        } else if (wParam == WM_KEYUP || wParam == WM_SYSKEYUP) {
            pressedKeys.erase(key);
        }
    }

    return CallNextHookEx(NULL, nCode, wParam, lParam);
}


// ==================================================================
// Capture Thread
// ==================================================================

void convertTo4BitBytes(const cv::Mat& grayscale8bit, std::vector<unsigned char>& output) {
    const uchar* src = grayscale8bit.ptr<uchar>();
    uchar* dst = output.data();
    int totalPixels = grayscale8bit.rows * grayscale8bit.cols;

    // Handle the bulk of the data
    int bulkPixels = totalPixels & (~1);  // This rounds down to the nearest even number
    for (int i = 0; i < bulkPixels; i += 2) {
        uchar pixel1 = src[i] >> 4;
        uchar pixel2 = src[i + 1] >> 4;

        // Pack the two 4-bit values into one byte
        *dst = (pixel1 << 4) | pixel2;
        ++dst;
    }

    // Handle the potential leftover pixel if totalPixels is odd
    if (totalPixels & 1) {
        uchar pixel1 = src[bulkPixels] >> 4;
        *dst = (pixel1 << 4); 
    }
}

void fillPacketWithKeys(FramePacket &packet, const std::set<KeyboardInput> &pressedKeys) {
    // Clear previous keys
    for (size_t i = 0; i < MAX_PRESSED_KEYS; ++i) {
        packet.pressedKeys[i] = {0, 0, 0};
    }

    size_t numKeysToCopy = std::min(pressedKeys.size(), MAX_PRESSED_KEYS);

    auto it = pressedKeys.begin();
    for (size_t i = 0; i < numKeysToCopy; ++i) {
        packet.pressedKeys[i] = *it;
        ++it;
    }

    if (pressedKeys.size() > MAX_PRESSED_KEYS) {
        std::cerr << "Warning: More keys pressed than can be sent in the packet. Overflow detected!" << std::endl;
    }
}

void send_loop(int sock, sockaddr_in server_address, int x, int y, int w, int h) {
    try {

        FramePacket packet = { 0 };
        ScreenCapturer capturer(x, y, w, h);

        packet.frameNumber = 0;

        // Preallocated buffers
        cv::Mat capturedImage;
        cv::Mat resizedImage(FRAME_HEIGHT, FRAME_WIDTH, CV_8UC4);
        std::vector<unsigned char> data4bit(FRAME_WIDTH * FRAME_HEIGHT / 2); // 4 bit
        std::pair<cv::Point, cv::Point> minimap = std::make_pair(cv::Point(0,0), cv::Point(0,0));

        // FPS values
        int frameCount = 0;
        auto desiredFrameTime = std::chrono::milliseconds(static_cast<int>(1000 / CAPTURE_TARGET_FPS));
        auto busyWaitThreshold = std::chrono::milliseconds(10);  // Adjust as needed

        auto startTime = std::chrono::high_resolution_clock::now();
        while (!stop_capture) {
            auto frameStartTime = std::chrono::high_resolution_clock::now();
            packet.frameNumber++;
            frameCount++;

            capturer.capture(capturedImage);

            // Calculate metrics
            packet.metrics = get_metric_percentages(capturedImage, w, h);

            // Populate the packet with pressed keys
            fillPacketWithKeys(packet, pressedKeys);

            // Convert BGRA to Grayscale
            cv::Mat grayscale;
            cv::cvtColor(capturedImage, grayscale, cv::COLOR_BGRA2GRAY);

            // Find Minimap bounds
            if (minimap.first.x == minimap.second.x) {
                minimap = find_minimap(grayscale);                
                std::cout << "Found Minimap at: (" 
                    << minimap.first.x << "," << minimap.first.y << ") -> ("
                    << minimap.second.x << "," << minimap.second.y << ")"
                    << std::endl;
            }

            // Extract the ROI (Region of Interest) corresponding to the minimap
            cv::Rect minimap_roi(minimap.first, minimap.second);
            cv::Mat minimap_image = grayscale(minimap_roi);

            // Find player and portal locations in minimap
            auto player = find_player(minimap_image, minimap);
            auto portals = find_portals(minimap_image, minimap);

            // Fill minimap data
            packet.minimap.width = minimap.second.x - minimap.first.x;
            packet.minimap.height = minimap.second.y - minimap.first.y;
            packet.minimap.playerX = player.x;
            packet.minimap.playerY = player.y;
            for (size_t i = 0; i < MAX_PORTALS; i++) {
                packet.minimap.portalX[i] = i < portals.size() ? portals[i].x : -1;
                packet.minimap.portalY[i] = i < portals.size() ? portals[i].y : -1;
            }

            // Resize the image
            cv::resize(grayscale, resizedImage, resizedImage.size());
 
            // cv::imwrite("capture.bmp", upscaled8bit);
            // cv::imwrite("minimap_debug.bmp", minimap_image);
            // exit(0);   
             
            // Convert to 4 bit
            convertTo4BitBytes(resizedImage, data4bit);  

            // Compress bytes
            uLongf length = MAX_BUFFER_SIZE;
            if (compress(&packet.data[0], &length, &data4bit[0], data4bit.size()) != Z_OK) {
                std::cerr << "Compression failed!" << std::endl;
                continue;
            }
            packet.length = length;

            // Send the frame             
            udp_send_to_server(sock, server_address, reinterpret_cast<const char*>(&packet), 
            FRAME_PACKET_HEADER_SIZE + packet.length);

            // Wait until next frame
            auto frameEndTime = std::chrono::high_resolution_clock::now();
            auto elapsedTime = std::chrono::duration_cast<std::chrono::milliseconds>(frameEndTime - frameStartTime);
            if (elapsedTime < desiredFrameTime) {
                std::this_thread::sleep_for(desiredFrameTime - elapsedTime  - busyWaitThreshold);
            }

            // Busy-wait loop
            while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - frameStartTime) < desiredFrameTime) {}
 
            // Report fps
            if (frameCount == CAPTURE_TARGET_FPS) {
                double fps = static_cast<double>(frameCount) / std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count();
                std::cout << "FPS: " << fps << std::endl;
                frameCount = 0;
                startTime = std::chrono::high_resolution_clock::now();
            }
        }
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
    }
}

// ==================================================================
// Action Thread
// ==================================================================

void processReceivedKeys(const ActionPacket& packet, std::set<KeyboardInput>& pressedKeys) {
    // Extract keys from packet and put them in a set
    std::set<KeyboardInput> receivedKeys;
    for (size_t i = 0; i < MAX_PRESSED_KEYS; ++i) {
        if (packet.pressedKeys[i].keyCode != NO_KEY_VALUE) {
            receivedKeys.insert(packet.pressedKeys[i]);
        }
    }

    // Press newly added keys
    for (const auto& key : receivedKeys) {
        if (pressedKeys.find(key) == pressedKeys.end()) {
            if (key.isVirtualKey) {
                press_virtual_key((WORD)key.keyCode);
            } else {
                press_scan_key((WORD)key.keyCode);
            }
            pressedKeys.insert(key);
        }
    }

    // Release removed keys
    for (auto it = pressedKeys.begin(); it != pressedKeys.end(); ) {
        if (receivedKeys.find(*it) == receivedKeys.end()) {
            if (it->isVirtualKey) {
                release_virtual_key((WORD)it->keyCode);
            } else {
                release_scan_key((WORD)it->keyCode);
            }
            it = pressedKeys.erase(it);
        } else {
            ++it;
        }
    }
}

void recv_loop(SOCKET sock, sockaddr_in server_address) {
    try {
        sockaddr_in from_address;
        int from_address_len = sizeof(from_address);

        // Keep track of currently pressed keys
        std::set<KeyboardInput> pressedKeys;

        while (!stop_capture) {
            ActionPacket actionPacket = { 0 };

            int bytes_received = udp_receive_from_server(
                sock, (char*)&actionPacket, sizeof(ActionPacket), &from_address, &from_address_len);

            if (bytes_received > 0) {
                processReceivedKeys(actionPacket, pressedKeys);
            }
        }
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
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

        // Sleep 1 second to allow to change window
        // TODO: set window focus
        std::this_thread::sleep_for(std::chrono::duration<double>(1.0));
            
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

        // Setup keyboard hook        
        HHOOK hHook = SetWindowsHookEx(WH_KEYBOARD_LL, LowLevelKeyboardProc, NULL, 0);
        if (!hHook) {
            DWORD error = GetLastError();
            CHAR buffer[255];
            sprintf(buffer, "SetWindowsHookEx failed with error: %lu", error);
            OutputDebugString(buffer);
        }

        // Create a socket
        SOCKET sock = udp_create_socket();
        sockaddr_in server_address = make_address(SERVER_IP, PORT);

        std::thread keyboard_thread(start_keyboard_listener);
        std::thread send_thread(send_loop, sock, server_address, x, y, w, h);
        std::thread recv_thread(recv_loop, sock, server_address);
    
        // Start a message loop for catching key events
        MSG msg;
        while (!stop_capture && GetMessage(&msg, NULL, 0, 0)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }

        keyboard_thread.join();
        send_thread.join();
        recv_thread.join();

        // Remove keyboard hook
        UnhookWindowsHookEx(hHook);

        // Close the socket
        close_socket(sock);

        // Cleanup Winsock
        cleanup_winsock();

        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
    }
}
