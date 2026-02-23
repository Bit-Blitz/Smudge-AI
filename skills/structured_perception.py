import uiautomation as auto
import psutil
import platform
import datetime
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger import logger

class StructuredPerception:
    def __init__(self):
        self.os_info = {
            "os": platform.system() + " " + platform.release(),
            "version": platform.version()
        }

    def capture_state(self):
        """Captures the current OS state into structured JSON."""
        logger.info("Capturing structured OS state...")
        
        try:
            # 1. System Info
            state = {
                "system": {
                    "os": self.os_info["os"],
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "focused_app": self._get_focused_app()
                },
                "open_windows": self._get_open_windows(),
                "taskbar_apps": self._get_taskbar_apps(), # Placeholder for now as this is tricky
                "installed_apps": [] # Placeholder, scanning takes time
            }
            return state
        except Exception as e:
            logger.error(f"Error capturing state: {e}")
            return {"error": str(e)}

    def _get_focused_app(self):
        try:
            window = auto.GetFocusedControl().GetTopLevelControl()
            return window.Name if window else "Unknown"
        except:
            return "Unknown"

    def _get_open_windows(self):
        windows = []
        try:
            # Enumerate top-level windows
            root = auto.GetRootControl()
            for window in root.GetChildren():
                if window.ControlTypeName == "WindowControl" and window.Name: # Filter valid windows
                     # Basic info
                    win_info = {
                        "title": window.Name,
                        "process_id": window.ProcessId,
                        "class_name": window.ClassName,
                        "controls": self._get_simple_controls(window)
                    }
                    windows.append(win_info)
        except Exception as e:
            logger.error(f"Error getting windows: {e}")
        return windows

    def _get_simple_controls(self, window_control):
        # Limited depth extraction to avoid performance hit
        controls = []
        try:
            # Get first level children
            for child in window_control.GetChildren():
                if child.ControlTypeName in ["ButtonControl", "EditControl", "ListControl", "MenuItemControl"]:
                    controls.append({
                        "type": child.ControlTypeName.replace("Control", "").lower(),
                        "label": child.Name,
                        "automation_id": child.AutomationId
                    })
        except:
            pass
        return controls

    def _get_taskbar_apps(self):
        # Placeholder implementation
        return ["Explorer", "Chrome", "VS Code"]

if __name__ == "__main__":
    sp = StructuredPerception()
    print(sp.capture_state())
