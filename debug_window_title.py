import ctypes
import time

def get_foreground_window_title():
    user32 = ctypes.windll.user32
    handle = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(handle)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(handle, buf, length + 1)
    return buf.value

print("Please focus the WhatsApp Desktop window within 5 seconds...")
time.sleep(5)
title = get_foreground_window_title()
print(f"Current Foreground Window Title: '{title}'")
