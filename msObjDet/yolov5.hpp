#pragma once
#include <vector>
#include <string>
#include <fstream>
#include <opencv2/opencv.hpp>

std::vector<std::string> load_class_list(const char* filename) {
    std::vector<std::string> class_list;
    std::ifstream ifs(filename);
    std::string line;
    while (getline(ifs, line)) {
        class_list.push_back(line);
    }
    return class_list;
}

void load_net(const char* filename, cv::dnn::Net &net) {
    auto result = cv::dnn::readNet(filename);
    std::cout << "Running on CPU\n";
    result.setPreferableBackend(cv::dnn::DNN_BACKEND_OPENCV);
    // result.setPreferableTarget(cv::dnn::DNN_TARGET_CPU);
    result.setPreferableTarget(cv::dnn::DNN_TARGET_OPENCL);
    net = result;
}

const int FRAME_SIZE = 1280;
const int OUTPUT_ROWS = 100800;
const int OUTPUT_DIMENSIONS = 11;
const float SCORE_THRESHOLD = 0.2;
const float NMS_THRESHOLD = 0.4;
const float CONFIDENCE_THRESHOLD = 0.4;

struct Detection {
    int class_id;
    float confidence;
    cv::Rect2d box;
};

void detect(cv::Mat &image, cv::dnn::Net &net, std::vector<Detection> &output, const std::vector<std::string> &className) {
    cv::Mat blob;

    // pad image to make it square
    int imageWidth = image.cols;
    int imageHeight = image.rows;
    int _dimension = FRAME_SIZE;
    cv::Mat input_image = cv::Mat::zeros(_dimension, _dimension, CV_8UC3);
    image.copyTo(input_image(cv::Rect(0, 0, image.cols, image.rows)));

    double factorX = 1 / double(imageWidth);
    double factorY = 1 / double(imageHeight);

    // run network
    cv::dnn::blobFromImage(input_image, blob, 1./255., cv::Size(input_image.cols, input_image.rows), cv::Scalar(), true, false);
    net.setInput(blob);
    std::vector<cv::Mat> outputs;
    net.forward(outputs, net.getUnconnectedOutLayersNames());
        
    float *data = (float *)outputs[0].data;
        
    std::vector<int> class_ids;
    std::vector<float> confidences;
    std::vector<cv::Rect2d> boxes;

    for (int i = 0; i < OUTPUT_ROWS; ++i) {

        float confidence = data[4];
        if (confidence >= CONFIDENCE_THRESHOLD) {

            float * classes_scores = data + 5;
            cv::Mat scores(1, className.size(), CV_32FC1, classes_scores);
            cv::Point class_id;
            double max_class_score;
            minMaxLoc(scores, 0, &max_class_score, 0, &class_id);
            if (max_class_score > SCORE_THRESHOLD) {
                confidences.push_back(confidence);
                class_ids.push_back(class_id.x);
                boxes.push_back(cv::Rect2f(data[0] * factorX, data[1] * factorY, 
                    data[2] * factorX, data[3] * factorY));
            }
        }

        data += OUTPUT_DIMENSIONS;
    }

    std::vector<int> nms_result;
    cv::dnn::NMSBoxes(boxes, confidences, SCORE_THRESHOLD, NMS_THRESHOLD, nms_result);
    for (size_t i = 0; i < nms_result.size(); i++) {
        int idx = nms_result[i];
        Detection result;
        result.class_id = class_ids[idx];
        result.confidence = confidences[idx];
        result.box = boxes[idx];
        output.push_back(result);
    }
}