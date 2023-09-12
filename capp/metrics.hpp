#pragma once
#include <windows.h>
#include <vector>
#include <map>
#include <string>
#include <algorithm>
#include "CImg.h"


struct Metrics {
    float hp, mp, exp;
};

struct MetricDimension {
    std::string name;
    int bottom_margin;
    int left_margin;
    int right_margin;
    std::string color;
};

const std::vector<MetricDimension> METRIC_DIMENSIONS = {
    {"HP", 45, 527, 584, "red"},
    {"MP", 29, 527, 584, "blue-green"},
    {"EXP", 3, 15, 0, "yellow-green"}
};

bool is_red(const BYTE* pixel) {
    float red = pixel[2];
    float green = pixel[1];
    float blue = pixel[0];

    if (red == 0) return false;

    float blue_to_red_ratio = blue / red;
    float green_to_red_ratio = green / red;

    return blue_to_red_ratio < 0.7 && green_to_red_ratio < 0.7 && red / 255.0f > 0.5;
}

bool is_blue_green(const BYTE* pixel) {
    float red = pixel[2];
    //float green = pixel[1];
    float blue = pixel[0];

    if (blue == 0) return false;

    float red_to_blue_ratio = red / blue;

    return red_to_blue_ratio < 0.7 && blue / 255.0f > 0.5;
}

bool is_yellow_green(const BYTE* pixel) {
    float red = pixel[2];
    float green = pixel[1];
    float blue = pixel[0];

    if (green == 0) return false;

    float blue_to_green_ratio = blue / green;

    return blue_to_green_ratio < 0.7 && green / 255.0f > 0.7 && red / 255.0f > 0.5;
}

Metrics get_metric_percentages(const cimg_library::CImg<unsigned char>& img_data, int frame_width, int frame_height) {
    Metrics metrics;

    for (const auto& metric : METRIC_DIMENSIONS) {
        int left_margin = metric.left_margin;
        int right_margin = metric.right_margin;
        int bottom_margin = metric.bottom_margin;

        int row_start_idx = (frame_width * (frame_height - bottom_margin) + left_margin) * 4; // 4 for BGRA
        int row_end_idx = (frame_width * (frame_height - bottom_margin) + frame_width - right_margin) * 4;

        std::vector<bool> row_processed;
        for (int i = row_start_idx; i < row_end_idx; i+=4) {
            if (metric.color == "red") {
                row_processed.push_back(is_red(&img_data[i]));
            } else if (metric.color == "blue-green") {
                row_processed.push_back(is_blue_green(&img_data[i]));
            } else if (metric.color == "yellow-green") {
                row_processed.push_back(is_yellow_green(&img_data[i]));
            }
        }

        auto first_true = std::find(row_processed.begin(), row_processed.end(), true);
        auto last_true = std::find(row_processed.rbegin(), row_processed.rend(), true);

        float value = 0;
        if (first_true != row_processed.end() && last_true != row_processed.rend()) {
            value = static_cast<float>(std::distance(first_true, last_true.base() - 1)) / static_cast<float>(row_processed.size() - 1);
        }

        if (metric.name == "HP") {
            metrics.hp = value;
        } else if (metric.name == "MP") {
            metrics.mp = value;
        } else if (metric.name == "EXP") {
            metrics.exp = value;
        }
    }

    return metrics;
}
