#pragma once
#include <iostream>
#include <vector>
#include <zlib.h>

std::vector<unsigned char> compressBytes(const std::vector<unsigned char>& data) {
    uLong compressedSize = compressBound(data.size());
    std::vector<unsigned char> compressedData(compressedSize);

    if (compress(&compressedData[0], &compressedSize, &data[0], data.size()) != Z_OK) {
        std::cerr << "Compression failed!" << std::endl;
        return {};
    }
    compressedData.resize(compressedSize);
    return compressedData;
}

std::vector<unsigned char> decompressBytes(const std::vector<unsigned char>& compressedData, uLong originalSize) {
    std::vector<unsigned char> decompressedData(originalSize);

    if (uncompress(&decompressedData[0], &originalSize, &compressedData[0], compressedData.size()) != Z_OK) {
        std::cerr << "Decompression failed!" << std::endl;
        return {};
    }
    return decompressedData;
}

// int main() {
//     std::vector<unsigned char> data = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};  // Example data
//     std::vector<unsigned char> compressedData = compressBytes(data);
//     std::vector<unsigned char> decompressedData = decompressBytes(compressedData, data.size());

//     // Print original, compressed, and decompressed data for verification
//     std::cout << "Original data: ";
//     for (auto byte : data) {
//         std::cout << (int)byte << " ";
//     }
//     std::cout << std::endl;

//     std::cout << "Compressed data: ";
//     for (auto byte : compressedData) {
//         std::cout << (int)byte << " ";
//     }
//     std::cout << std::endl;

//     std::cout << "Decompressed data: ";
//     for (auto byte : decompressedData) {
//         std::cout << (int)byte << " ";
//     }
//     std::cout << std::endl;

//     return 0;
// }
