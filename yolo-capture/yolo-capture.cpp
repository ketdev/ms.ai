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
#include "yolov5.hpp"

// ==================================================================
// Constants
// ==================================================================

// const char* const TARGET_WINDOW_NAME = "*Untitled - Notepad";
const char* const TARGET_WINDOW_NAME = "MapleStory";

const int CAPTURE_TARGET_FPS = 6;

const char* const CLASSES_FILENAME = "./model/classes.txt";
const char* const MODEL_FILENAME = "./model/msai_yolov5s.onnx";

const std::vector<cv::Scalar> colors = {cv::Scalar(255, 255, 0), cv::Scalar(0, 255, 0), cv::Scalar(0, 255, 255), cv::Scalar(255, 0, 0)};

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

        // load yolov5 
        std::vector<std::string> class_list = load_class_list(CLASSES_FILENAME);

        cv::dnn::Net net;
        bool is_cuda = false;
        load_net(MODEL_FILENAME, net, is_cuda);

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

            // Perform detection
            std::vector<Detection> output;
            detect(capturedImage, net, output, class_list);

            // Save if there is a detection with low confidence
            bool save = false;
            for (int i = 0; i < output.size(); ++i) {
                auto detection = output[i];
                if (detection.confidence < CONFIDENCE_THRESHOLD) {
                    save = true;
                    break;
                }
            }

            if (save) {                
                std::string frame_filename = "frame_" + std::to_string(frameCount) + ".bmp";
                std::string output_filename = "frame_" + std::to_string(frameCount) + ".txt";

                // Write frame to file
                cv::imwrite(frame_filename.c_str(), capturedImage);

                // Write detection to file
                std::ofstream output_file;
                output_file.open(output_filename.c_str());
                for (int i = 0; i < output.size(); ++i) {
                    auto detection = output[i];
                    auto box = detection.box;
                    auto classId = detection.class_id;
                    output_file << class_list[classId] << " " << box.x << " " << box.y << " " << box.width << " " << box.height << std::endl;
                }
            }            

            // Debug show
            for (int i = 0; i < output.size(); ++i) {
                auto detection = output[i];
                auto box = detection.box;
                auto classId = detection.class_id;
                const auto color = colors[classId % colors.size()];
                cv::rectangle(capturedImage, box, color, 3);

                cv::rectangle(capturedImage, cv::Point(box.x, box.y - 20), cv::Point(box.x + box.width, box.y), color, cv::FILLED);
                cv::putText(capturedImage, class_list[classId].c_str(), cv::Point(box.x, box.y - 5), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(0, 0, 0));
            }
            cv::imshow("output", capturedImage);

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
