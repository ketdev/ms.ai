#pragma once
// Image dimensions: width = 8, height = 8, channels = 1
// To create cv::Mat in C++:
// cv::Mat img(8, 8, CV_8UC1, player_template_data);
unsigned char player_template_data[64] = {
    0xaf, 0x88, 0x33, 0x33, 0x33, 0x33, 0x88, 0xb0, 0x88, 0x33, 0x8b, 0xdc, 
    0xdc, 0x8b, 0x33, 0x88, 0x33, 0x8b, 0xdc, 0xd6, 0xd6, 0xdc, 0x8b, 0x33, 
    0x33, 0xdc, 0xd6, 0xd6, 0xd6, 0xd6, 0xdc, 0x33, 0x33, 0xdc, 0xd6, 0xd6, 
    0xd6, 0xd6, 0xdc, 0x33, 0x33, 0x8b, 0xdc, 0xd6, 0xd6, 0xdc, 0x8b, 0x33, 
    0x88, 0x33, 0x8b, 0xdc, 0xdc, 0x8b, 0x33, 0x88, 0xaf, 0x88, 0x33, 0x33, 
    0x33, 0x33, 0x88, 0xb0
};