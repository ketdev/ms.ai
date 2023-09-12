#pragma once
#include <windows.h>
#include <opencv2/opencv.hpp>

class ScreenCapturer {
private:
    HDC hdcScreen;
    HDC hdcMemoryDC;
    HBITMAP hBitmap;
    int width, height;

public:
    ScreenCapturer(int x, int y, int w, int h) : width(w), height(h) {
        hdcScreen = GetDC(NULL);
        hdcMemoryDC = CreateCompatibleDC(hdcScreen);
        hBitmap = CreateCompatibleBitmap(hdcScreen, width, height);
        SelectObject(hdcMemoryDC, hBitmap);
    }

    cv::Mat capture(int x, int y) {
        BitBlt(hdcMemoryDC, 0, 0, width, height, hdcScreen, x, y, SRCCOPY);
        
        cv::Mat mat(cv::Size(width, height), CV_8UC4);
        GetBitmapBits(hBitmap, mat.dataend - mat.datastart, mat.data);
        
        return mat;
    }

    ~ScreenCapturer() {
        DeleteObject(hBitmap);
        DeleteDC(hdcMemoryDC);
        ReleaseDC(NULL, hdcScreen);
    }
};
