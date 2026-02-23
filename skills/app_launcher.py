import os
import subprocess
import time
import psutil
import uiautomation as auto
import logging

class AppLauncher:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def open_app(self, app_name, app_path=None):
        self.logger.info(f"Opening app: {app_name}")
        
        # Check if already running
        for proc in psutil.process_iter(['name']):
            if app_name.lower() in proc.info['name'].lower():
                self.logger.info(f"{app_name} is already running. Focusing...")
                self.focus_app(app_name)
                return True

        # Launch
        try:
            if app_path:
                subprocess.Popen(app_path)
            else:
                # Try Windows Search/Run
                # Specific check for WhatsApp to use protocol handler
                if app_name.lower() == "whatsapp":
                    self.logger.info("Using protocol handler for WhatsApp")
                    os.system("start whatsapp:")
                    time.sleep(3) # Wait for UWP app to launch
                    return True
                    
                subprocess.Popen(["cmd", "/c", "start", app_name]) # This might not work for all apps
                # Alternatively use `os.startfile(app_name)`
                # os.startfile(app_name) # Requires valid path or registered app
            
            # Wait for it to open
            time.sleep(2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to open app {app_name}: {e}")
            return False

    def close_app(self, app_name):
        self.logger.info(f"Closing app: {app_name}")
        for proc in psutil.process_iter(['name']):
            if app_name.lower() in proc.info['name'].lower():
                proc.kill()
                return True
        return False

    def focus_app(self, app_name):
        # Focus logic using uiautomation
        try:
            # Simple approach: find window by name
            window = auto.WindowControl(searchDepth=1, Name=app_name) # This is partial match, might need regex
            if window.Exists(maxSearchSeconds=1):
                window.SetFocus()
                return True
            else:
                # Try partial match on all windows
                for win in auto.GetRootControl().GetChildren():
                    if app_name.lower() in win.Name.lower():
                        win.SetFocus()
                        return True
        except Exception as e:
            self.logger.error(f"Failed to focus app {app_name}: {e}")
        return False
