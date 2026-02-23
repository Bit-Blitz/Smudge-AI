import os
import time
import pyautogui
import pyperclip
from utils.logger import logger
from skills.app_launcher import AppLauncher

class DesktopAppController:
    def __init__(self):
        self.app_launcher = AppLauncher()

    def _safe_paste(self, text):
        """Safely pastes text using clipboard to avoid slow typing."""
        try:
            pyperclip.copy(text)
            time.sleep(0.1) # Wait for clipboard to update
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Clipboard paste failed: {e}")
            # Fallback to typing if paste fails
            pyautogui.write(text)

    def _is_focused(self):
        """Checks if WhatsApp is the foreground window."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            handle = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(handle)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(handle, buf, length + 1)
            title = buf.value
            # Debug log to see what window is actually focused
            # logger.debug(f"Current window: '{title}'") 
            return "whatsapp" in title.lower()
        except:
            return True # Fail open to be safe? Or False? Let's say True to avoid blocking if check fails.

    def _wait_for_focus(self, timeout=5.0):
        """Waits for WhatsApp to become the foreground window."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_focused():
                return True
            time.sleep(0.5)
        return False

    def send_whatsapp_desktop_message(self, target, message):
        """
        Interacts with the native WhatsApp Desktop application to send a message.
        """
        logger.info(f"Attempting to send WhatsApp Desktop message to {target}")
        
        # 1. Open/Focus WhatsApp
        # Force protocol launch to ensure it opens even if closed
        os.system("start whatsapp:")
        
        # Wait for app to actually appear and grab focus
        if not self._wait_for_focus(timeout=5.0):
             logger.warning("WhatsApp failed to gain focus within 5 seconds. Aborting.")
             return False
        
        try:
            # 2. Search for contact
            # "Reset" state to ensure no other chat/search is open
            pyautogui.press('esc')
            time.sleep(0.1)
            pyautogui.press('esc') 
            time.sleep(0.2)
            
            # Use Ctrl+N (New Chat) which is more reliable for finding people than Ctrl+F (Find in chat)
            pyautogui.hotkey('ctrl', 'n')
            time.sleep(0.5)
            
            # Paste contact name/number (Faster than typing)
            self._safe_paste(target)
            time.sleep(1.0) # Wait for search results
            
            if not self._is_focused():
                logger.warning("WhatsApp lost focus during search. Aborting.")
                return False

            # Select first result
            pyautogui.press('down')
            time.sleep(0.1)
            pyautogui.press('enter')
            time.sleep(0.5) # Wait for chat to open
            
            # 3. Type and send message
            self._safe_paste(message)
            time.sleep(0.1)
            pyautogui.press('enter')
            
            logger.info("Message sent via WhatsApp Desktop")
            return True
            
        except Exception as e:
            logger.error(f"Failed to control WhatsApp Desktop: {e}")
            return False

if __name__ == "__main__":
    dac = DesktopAppController()
    # dac.send_whatsapp_desktop_message("Mom", "Hello from Desktop App")
