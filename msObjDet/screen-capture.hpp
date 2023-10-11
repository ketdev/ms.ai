#pragma once
#include <windows.h>
#include <opencv2/core.hpp>
#include <vector>

class ScreenCapturer {
   private:
    HDC hdcScreen;
    HDC hdcMemoryDC;
    HBITMAP hBitmap;
    int x, y;
    int width, height;

   public:
    // Get client rectangle of a window by its name
    static RECT GetClientRectangle(const char *windowName) {
        HWND hwnd = FindWindowA(NULL, windowName);
        if (!hwnd) {
            // Window not found
            return {0, 0, 0, 0};
        }

        RECT clientRect;
        GetClientRect(hwnd, &clientRect);

        POINT ptTopLeft = {clientRect.left, clientRect.top};
        POINT ptBottomRight = {clientRect.right, clientRect.bottom};
        ClientToScreen(hwnd, &ptTopLeft);
        ClientToScreen(hwnd, &ptBottomRight);

        clientRect.left = ptTopLeft.x;
        clientRect.top = ptTopLeft.y;
        clientRect.right = ptBottomRight.x;
        clientRect.bottom = ptBottomRight.y;

        return clientRect;
    }

    ScreenCapturer(int x, int y, int w, int h)
        : x(x), y(y), width(w), height(h) {
        hdcScreen = GetDC(NULL);
        hdcMemoryDC = CreateCompatibleDC(hdcScreen);
        hBitmap = CreateCompatibleBitmap(hdcScreen, width, height);
        SelectObject(hdcMemoryDC, hBitmap);
    }

    void capture(cv::Mat &image) {
        BitBlt(hdcMemoryDC, 0, 0, width, height, hdcScreen, x, y, SRCCOPY);

        BITMAPINFOHEADER bi;
        bi.biSize = sizeof(BITMAPINFOHEADER);
        bi.biWidth = width;
        bi.biHeight = -height;  // This line makes it draw upside down or not
        bi.biPlanes = 1;
        bi.biBitCount = 32;
        bi.biCompression = BI_RGB;
        bi.biSizeImage = 0;
        bi.biXPelsPerMeter = 0;
        bi.biYPelsPerMeter = 0;
        bi.biClrUsed = 0;
        bi.biClrImportant = 0;

        // Calculate stride
        // DWORD dwStride = ((width * bi.biBitCount + 31) / 32) * 4;

        if (image.empty() || image.cols != width || image.rows != height ||
            image.type() != CV_8UC4) {
            image.create(height, width, CV_8UC4);  // BGRA format
        }

        GetDIBits(hdcMemoryDC, hBitmap, 0, (UINT)height, image.data,
                  (BITMAPINFO *)&bi, DIB_RGB_COLORS);
    }

    ~ScreenCapturer() {
        DeleteObject(hBitmap);
        DeleteDC(hdcMemoryDC);
        ReleaseDC(NULL, hdcScreen);
    }
};
