#pragma once
#include <iostream>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

void initialize_winsock() {
    WSADATA wsaData;
    int iResult = WSAStartup(MAKEWORD(2,2), &wsaData);
    if (iResult != 0) {
        std::cerr << "WSAStartup failed: " << iResult << "\n";
        exit(1);
    }
}

SOCKET tcp_create_socket() {
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        std::cerr << "Error at socket(): " << WSAGetLastError() << "\n";
        WSACleanup();
        exit(1);
    }
    return sock;
}

sockaddr_in make_address(const char* ip, int port) {
    sockaddr_in serv_addr;
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(port);
    serv_addr.sin_addr.s_addr = inet_addr(ip);
    return serv_addr;
}

void tcp_connect_to_server(SOCKET sock, const sockaddr_in& serv_addr) {
    if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) == SOCKET_ERROR) {
        std::cerr << "Failed to connect: " << WSAGetLastError() << "\n";
        closesocket(sock);
        WSACleanup();
        exit(1);
    }
}

SOCKET udp_create_socket() {
    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET) {
        std::cerr << "Error at socket(): " << WSAGetLastError() << "\n";
        WSACleanup();
        exit(1);
    }
    return sock;
}

int udp_send_to_server(SOCKET sock, const sockaddr_in& serv_addr, const char* data, int length) {
    return sendto(sock, data, length, 0, (struct sockaddr*)&serv_addr, sizeof(serv_addr));
}

int udp_receive_from_server(SOCKET sock, char* buffer, int buffer_length, sockaddr_in* from = nullptr, int* from_length = nullptr) {
    if (from && from_length) {
        return recvfrom(sock, buffer, buffer_length, 0, (struct sockaddr*)from, from_length);
    } else {
        return recvfrom(sock, buffer, buffer_length, 0, nullptr, nullptr);
    }
}


void close_socket(SOCKET sock) {
    closesocket(sock);
}

void cleanup_winsock() {
    WSACleanup();
}