import time
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger import logger
from skills.app_launcher import AppLauncher
from skills.structured_perception import StructuredPerception
from skills.browser_controller import BrowserController
from skills.filesystem_manager import FilesystemManager
from skills.openclaw_client import OpenClawClient
from skills.desktop_app_controller import DesktopAppController
from skills.whatsapp_api_client import WhatsAppAPIClient

class Executor:
    def __init__(self):
        self.app_launcher = AppLauncher()
        self.perception = StructuredPerception()
        self.browser_controller = BrowserController()
        self.filesystem_manager = FilesystemManager()
        self.openclaw = OpenClawClient()
        self.desktop_controller = DesktopAppController()
        self.whatsapp_api = WhatsAppAPIClient()

    def execute_plan(self, plan):
        """Executes the given plan."""
        logger.info(f"Executing plan: {plan}")
        
        action = plan.get("action")
        target = plan.get("target")
        strategy = plan.get("strategy")
        
        if not action:
            logger.error("No action specified in plan.")
            return False
            
        try:
            if action == "open_app":
                return self.app_launcher.open_app(target)
            elif action == "close_app":
                return self.app_launcher.close_app(target)
            elif action == "focus_app":
                return self.app_launcher.focus_app(target)
            elif action == "type_text":
                import pyautogui
                pyautogui.write(target)
                return True
            elif action == "press_key":
                import pyautogui
                pyautogui.press(target)
                return True
            elif action == "click_element":
                coordinates = plan.get("coordinates")
                if coordinates and len(coordinates) == 2:
                    import pyautogui
                    pyautogui.click(x=coordinates[0], y=coordinates[1])
                    return True
                else:
                    logger.warning(f"click_element requires coordinates, got: {coordinates}")
                    return False
            elif action == "run_command":
                logger.info(f"Running command: {target}")
                # Special handling for 'code' command to ensure it opens properly
                if target.startswith("code "):
                    # If target has a file path, try to resolve it to absolute path if possible
                    parts = target.split(" ", 1)
                    if len(parts) > 1:
                        file_arg = parts[1]
                        # Use filesystem manager logic or simple expansion
                        if not os.path.isabs(file_arg):
                             # Try to match what FilesystemManager does (Downloads default)
                             # But here we don't know for sure where it wrote. 
                             # Ideally, the planner should have passed the full path.
                             # Let's assume Downloads if it looks like a bare filename
                             if not os.path.dirname(file_arg):
                                 downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                                 possible_path = os.path.join(downloads_path, file_arg)
                                 if os.path.exists(possible_path):
                                     target = f"code \"{possible_path}\""
                
                # Use subprocess for better control
                import subprocess
                try:
                    subprocess.Popen(target, shell=True)
                    return True
                except Exception as e:
                    logger.error(f"Command failed: {e}")
                    return False
            elif action == "open_url":
                return self.browser_controller.open_url(target)
            elif action == "play_media":
                # 'target' is the search query
                # 'strategy' can specify platform (youtube, spotify)
                strategy = plan.get("strategy", "").lower()
                if "spotify" in strategy:
                    return self.browser_controller.play_spotify(target)
                else:
                    return self.browser_controller.play_youtube(target)
            elif action == "send_message":
                # 'target' is phone number OR contact name
                target_contact = target
                message = plan.get("content", "")
                strategy = plan.get("strategy", "").lower()
                
                if "whatsapp" in strategy:
                    if "api" in strategy or "cloud" in strategy:
                        # Use Cloud API if explicitly requested or if Desktop fails?
                        # For now, explicit request.
                        if self.whatsapp_api.is_available():
                            return self.whatsapp_api.send_message(target_contact, message)
                        else:
                            logger.warning("WhatsApp Cloud API requested but not configured. Falling back to Desktop.")
                            return self.desktop_controller.send_whatsapp_desktop_message(target_contact, message)
                    elif "desktop" in strategy or "app" in strategy:
                        return self.desktop_controller.send_whatsapp_desktop_message(target_contact, message)
                    else:
                        # Default to Desktop if not specified (since it's more robust now)
                        return self.desktop_controller.send_whatsapp_desktop_message(target_contact, message)
                else:
                    logger.warning(f"Unknown messaging platform in strategy: {strategy}")
                    return False
            elif action == "write_file":
                content = plan.get("content", "")
                result_path = self.filesystem_manager.write_file(target, content)
                if result_path:
                    logger.info(f"File successfully created at: {result_path}")
                    # You might want to bubble this up to the user somehow
                    return {"status": "success", "message": f"File created at: {result_path}", "path": result_path}
                else:
                    return False
            elif action == "delegate_to_openclaw":
                result = self.openclaw.execute_task(target)
                logger.info(f"OpenClaw Result: {result}")
                return True
            else:
                logger.warning(f"Unknown action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            return False

if __name__ == "__main__":
    executor = Executor()
    executor.execute_plan({"action": "open_app", "target": "Notepad"})
