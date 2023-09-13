#include <chrono>
#include <cstring>
#include <iostream>
#include <atomic>
#include <thread>
#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/opencv.hpp>

#include "network.hpp"
#include "input.hpp"
#include "metrics.hpp"
#include "protocol.hpp"
#include "screen-capture.hpp"

// ==================================================================
// Constants
// ==================================================================

const char* const SERVER_IP = "10.0.0.6";
const int PORT = 12345;

const char* const TARGET_WINDOW_NAME = "MapleStory"; // "Untitled - Notepad";

const int CAPTURE_TARGET_FPS = 20;

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
            break;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

// ==================================================================
// Utils
// ==================================================================

cv::Mat convertTo4Bit(const cv::Mat& grayscale8bit) {
    cv::Mat grayscale4bit;
    grayscale8bit.convertTo(grayscale4bit, CV_8U, 1.0/16.0);
    return grayscale4bit;
}

cv::Mat upscaleTo8Bit(const cv::Mat& grayscale4bit) {
    cv::Mat upscaled8bit;
    grayscale4bit.convertTo(upscaled8bit, CV_8U, 16.0);
    return upscaled8bit;
}

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

void send_metrics(int sock, const sockaddr_in& server_address,
                  const Metrics& metrics) {
    UDPPacket packet;
    packet.type = METRICS;
    packet.header_data = metrics;
    udp_send_to_server(sock, server_address,
                       reinterpret_cast<const char*>(&packet), sizeof(packet));
}

void send_chunks(SOCKET sock, const sockaddr_in& server_address, const std::vector<unsigned char>& data4bit) {
    // Calculate total number of bytes for a full image
    const int totalBytes = FRAME_WIDTH * FRAME_HEIGHT / 2; // Dividing by 2 because it's 4-bit

    // Calculate total number of chunks required to send the image
    const int totalChunks = totalBytes / CHUNK_SIZE;

    for (int chunkIndex = 0; chunkIndex < totalChunks; ++chunkIndex) {
        UDPPacket chunkPacket;
        chunkPacket.type = CHUNK;
        chunkPacket.chunk_data.row_index = chunkIndex; 

        // Get a pointer to the start of the current chunk in the data4bit vector
        const unsigned char* startPtr = &data4bit[chunkIndex * CHUNK_SIZE];

        // Copy the required bytes into the chunk data
        std::memcpy(chunkPacket.chunk_data.chunk_data, startPtr, CHUNK_SIZE);

        // Send the chunk 
        udp_send_to_server(sock, server_address, reinterpret_cast<const char*>(&chunkPacket), sizeof(chunkPacket));
    }
}


// ==================================================================
// Main Processes
// ==================================================================

void send_loop(int sock, sockaddr_in server_address, int x, int y, int w,
               int h) {
    try {
        int frameCount = 0;

        ScreenCapturer capturer(x, y, w, h);

        // Preallocated buffers
        cv::Mat capturedImage;
        cv::Mat resizedImage(FRAME_HEIGHT, FRAME_WIDTH, CV_8UC4);
        cv::Mat grayscale(FRAME_HEIGHT, FRAME_WIDTH, CV_8UC1);
        std::vector<unsigned char> data4bit(FRAME_WIDTH * FRAME_HEIGHT / 2); // 4 bit

        std::cout << "Sending chunks of size: " << sizeof(UDPPacket) << std::endl;

        auto desiredFrameTime = std::chrono::milliseconds(static_cast<int>(1000 / CAPTURE_TARGET_FPS));
        auto busyWaitThreshold = std::chrono::milliseconds(10);  // Adjust as needed

        auto startTime = std::chrono::high_resolution_clock::now();
        while (!stop_capture) {
            auto frameStartTime = std::chrono::high_resolution_clock::now();
            frameCount++;

            capturer.capture(capturedImage);

            // Calculate metrics
            Metrics metrics = get_metric_percentages(capturedImage, w, h);

            // Resize the image
            cv::resize(capturedImage, resizedImage, resizedImage.size());

            // Convert BGRA to Grayscale
            cv::Mat grayscale;
            cv::cvtColor(resizedImage, grayscale, cv::COLOR_BGRA2GRAY);

            // Convert to 4 bit
            convertTo4BitBytes(grayscale, data4bit);

            // cv::Mat gray4bit = convertTo4Bit(grayscale);
            // cv::Mat upscaled8bit = upscaleTo8Bit(gray4bit);
            // cv::imwrite("capture.bmp", upscaled8bit);
            // exit(0);  
 
            // Send
            send_metrics(sock, server_address, metrics);
            send_chunks(sock, server_address, data4bit);

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

void recv_loop(SOCKET sock, sockaddr_in server_address) {
    try {
        sockaddr_in from_address;
        int from_address_len = sizeof(from_address);

        while (!stop_capture) {
            uint8_t action = 0;

            int bytes_received = udp_receive_from_server(
                sock, (char*)&action, 1, &from_address, &from_address_len);

            // if (bytes_received > 0) {
            //     std::cout << "Action: " << (int)action << " from "
            //               << inet_ntoa(from_address.sin_addr) << ":"
            //               << ntohs(from_address.sin_port) << std::endl;
            // }
        }
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
    }
}

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

        // Initialize Winsock
        initialize_winsock();

        // Create a socket
        SOCKET sock = udp_create_socket();
        sockaddr_in server_address = make_address(SERVER_IP, PORT);

        std::thread keyboard_thread(start_keyboard_listener);
        std::thread send_thread(send_loop, sock, server_address, x, y, w, h);
        std::thread recv_thread(recv_loop, sock, server_address);

        keyboard_thread.join();
        send_thread.join();
        recv_thread.join();

        // Close the socket
        close_socket(sock);

        // Cleanup Winsock
        cleanup_winsock();

        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
    }
}
