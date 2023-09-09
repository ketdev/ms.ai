import ctypes

SendInput = ctypes.windll.user32.SendInput

# Constants
KEYEVENTF_KEYUP = 0x2
KEYEVENTF_SCANCODE = 0x8

def press_key(hex_key_code):
    extra = ctypes.c_ulong(0)
    ii_ = ctypes.c_input(1, ctypes.c_void_p(0))
    
    ii_.ki = ctypes.keybd_input(0, hex_key_code, KEYEVENTF_SCANCODE, 0, ctypes.pointer(extra))
    x = ctypes.input((ii_,))
    SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def release_key(hex_key_code):
    extra = ctypes.c_ulong(0)
    ii_ = ctypes.c_input(1, ctypes.c_void_p(0))
    
    ii_.ki = ctypes.keybd_input(0, hex_key_code, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    x = ctypes.input((ii_,))
    SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

# Example of pressing and releasing the 'A' key using its scan code
press_key(0x1E)
release_key(0x1E)
