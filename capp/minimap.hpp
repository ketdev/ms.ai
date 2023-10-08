#pragma once
#include <vector>
#include <opencv2/opencv.hpp>

#include "assets/minimap_br_template_data.hpp"
#include "assets/minimap_tl_template_data.hpp"
#include "assets/player_template_data.hpp"
#include "assets/portal_template_data.hpp"

// Minimap template images
const int MINIMAP_TOP_BORDER = 5;
const int MINIMAP_BOTTOM_BORDER = 9;

cv::Mat MM_TL_TEMPLATE(11, 15, CV_8UC1, minimap_tl_template_data);
cv::Mat MM_BR_TEMPLATE(22, 37, CV_8UC1, minimap_br_template_data);
cv::Mat PLAYER_TEMPLATE(8, 8, CV_8UC1, player_template_data);
cv::Mat PORTAL_TEMPLATE(8, 8, CV_8UC1, portal_template_data);

const int MMT_HEIGHT = std::max(MM_TL_TEMPLATE.rows, MM_BR_TEMPLATE.rows);
const int MMT_WIDTH = std::max(MM_TL_TEMPLATE.cols, MM_BR_TEMPLATE.cols);


std::pair<cv::Point, cv::Point> single_match(const cv::Mat& gray, const cv::Mat& templateImg) {
    cv::Mat result;
    cv::matchTemplate(gray, templateImg, result, cv::TM_CCOEFF);

    double minVal, maxVal;
    cv::Point minLoc, maxLoc, top_left;
    cv::minMaxLoc(result, &minVal, &maxVal, &minLoc, &maxLoc);

    top_left = maxLoc;

    cv::Point bottom_right(top_left.x + templateImg.cols, top_left.y + templateImg.rows);
    return std::make_pair(top_left, bottom_right);
}

std::vector<std::pair<cv::Point, cv::Point>> multi_match(const cv::Mat& gray, const cv::Mat& templ, double threshold = 0.95) {
    // Check if template size is larger than frame
    if (templ.rows > gray.rows || templ.cols > gray.cols) {
        return {};
    }

    // Match template
    cv::Mat result;
    cv::matchTemplate(gray, templ, result, cv::TM_CCOEFF_NORMED);

    // Find locations with matches that exceed the threshold
    std::vector<cv::Point> matchLocations;
    cv::Mat mask;
    cv::threshold(result, mask, threshold, 1.0, cv::THRESH_BINARY);
    mask.convertTo(mask, CV_8U);

    // Fetch points from the mask
    cv::findNonZero(mask, matchLocations);

    std::vector<std::pair<cv::Point, cv::Point>> matches;
    for (const cv::Point& topLeft : matchLocations) {
        cv::Point bottomRight(topLeft.x + templ.cols, topLeft.y + templ.rows);
        matches.push_back({topLeft, bottomRight});
    }

    return matches;
}


std::pair<cv::Point, cv::Point> find_minimap(const cv::Mat& gray) {
    auto tl_match = single_match(gray, MM_TL_TEMPLATE);
    auto br_match = single_match(gray, MM_BR_TEMPLATE);
    auto mm_tl = cv::Point(
        tl_match.first.x + MINIMAP_BOTTOM_BORDER, 
        tl_match.first.y + MINIMAP_TOP_BORDER
    );
    auto mm_br = cv::Point(
        std::max(mm_tl.x + MMT_WIDTH, br_match.second.x - MINIMAP_BOTTOM_BORDER),
        std::max(mm_tl.y + MMT_HEIGHT, br_match.second.y - MINIMAP_BOTTOM_BORDER)
    );

    return std::make_pair(mm_tl, mm_br);
}

cv::Point find_player(const cv::Mat& minimap_gray, const std::pair<cv::Point, cv::Point>& minimap) {
    std::vector<std::pair<cv::Point, cv::Point>> playerMatches = multi_match(minimap_gray, PLAYER_TEMPLATE, 0.8);
    if (!playerMatches.empty()) {
        auto p_tl = playerMatches[0].first;
        auto p_br = playerMatches[0].second;
        auto px = (p_tl.x + p_br.x) * 0.5;
        auto py = (p_tl.y + p_br.y) * 0.5;
        return cv::Point(px, py);
    }
    return cv::Point(-1,-1);
}

std::vector<cv::Point> find_portals(const cv::Mat& minimap_gray, const std::pair<cv::Point, cv::Point>& minimap) {
    std::vector<std::pair<cv::Point, cv::Point>> portalMatches = multi_match(minimap_gray, PORTAL_TEMPLATE, 0.8);
    std::vector<cv::Point> result;
    for (size_t i = 0; i < portalMatches.size(); i++) {        
        auto p_tl = portalMatches[i].first;
        auto p_br = portalMatches[i].second;
        auto px = (p_tl.x + p_br.x) * 0.5;
        auto py = (p_tl.y + p_br.y) * 0.5;
        result.push_back(cv::Point(px, py));
    }
    return result;
}

