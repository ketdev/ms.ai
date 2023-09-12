#pragma once
#include <windows.h>
#include <vector>
#include "CImg.h"

class ScreenCapturer {
private:
    HDC hdcScreen;
    HDC hdcMemoryDC;
    HBITMAP hBitmap;
    int x, y;
    int width, height;

public:
    // Get client rectangle of a window by its name
    static RECT GetClientRectangle(const char* windowName) {
        HWND hwnd = FindWindowA(NULL, windowName);
        if (!hwnd) {
            // Window not found
            return { 0, 0, 0, 0 };
        }

        RECT clientRect;
        GetClientRect(hwnd, &clientRect);

        POINT ptTopLeft = { clientRect.left, clientRect.top };
        POINT ptBottomRight = { clientRect.right, clientRect.bottom };
        ClientToScreen(hwnd, &ptTopLeft);
        ClientToScreen(hwnd, &ptBottomRight);

        clientRect.left = ptTopLeft.x;
        clientRect.top = ptTopLeft.y;
        clientRect.right = ptBottomRight.x;
        clientRect.bottom = ptBottomRight.y;

        return clientRect;
    }

    ScreenCapturer(int x, int y, int w, int h) : x(x), y(y), width(w), height(h) {
        hdcScreen = GetDC(NULL);
        hdcMemoryDC = CreateCompatibleDC(hdcScreen);
        hBitmap = CreateCompatibleBitmap(hdcScreen, width, height);
        SelectObject(hdcMemoryDC, hBitmap);
    }

    std::vector<BYTE> capture_bytes() {
        BitBlt(hdcMemoryDC, 0, 0, width, height, hdcScreen, x, y, SRCCOPY);

        BITMAPINFOHEADER bi;
        bi.biSize = sizeof(BITMAPINFOHEADER);
        bi.biWidth = width;
        bi.biHeight = -height;  // This is the line that makes it draw upside down or not
        bi.biPlanes = 1;
        bi.biBitCount = 32;
        bi.biCompression = BI_RGB;
        bi.biSizeImage = 0;
        bi.biXPelsPerMeter = 0;
        bi.biYPelsPerMeter = 0;
        bi.biClrUsed = 0;
        bi.biClrImportant = 0;

        // Calculate stride
        DWORD dwStride = ((width * bi.biBitCount + 31) / 32) * 4;
        DWORD dwBmpSize = dwStride * height;

        auto lpBitmap = std::vector<BYTE>(dwBmpSize);
        GetDIBits(hdcMemoryDC, hBitmap, 0, (UINT)height, &lpBitmap[0], (BITMAPINFO *)&bi, DIB_RGB_COLORS);

        return lpBitmap;
    }

    cimg_library::CImg<unsigned char> capture() {
        BitBlt(hdcMemoryDC, 0, 0, width, height, hdcScreen, x, y, SRCCOPY);
        BITMAPINFOHEADER bi = { sizeof(BITMAPINFOHEADER), width, -height, 1, 32, BI_RGB, 0, 0, 0, 0, 0 };
        cimg_library::CImg<unsigned char> img(width, height, 1, 4);
        img.fill(0);  // fill the image with 0
        GetDIBits(hdcMemoryDC, hBitmap, 0, height, img.data(), (BITMAPINFO *)&bi, DIB_RGB_COLORS);
        return img;
    }

    ~ScreenCapturer() {
        DeleteObject(hBitmap);
        DeleteDC(hdcMemoryDC);
        ReleaseDC(NULL, hdcScreen);
    }
};
