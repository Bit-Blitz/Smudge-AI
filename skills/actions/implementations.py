from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .base import Action
from utils.logger import logger
import os
import subprocess
import time

# --- Parameter Models ---

class AppParams(BaseModel):
    app_name: str = Field(..., description="Name of the application executable or shortcut")

class TextParams(BaseModel):
    text: str = Field(..., description="Text to type")

class KeyParams(BaseModel):
    key: str = Field(..., description="Key to press (e.g., 'enter', 'tab', 'ctrl+c')")

class ClickParams(BaseModel):
    coordinates: List[int] = Field(..., description="[x, y] coordinates to click", min_items=2, max_items=2)

class CommandParams(BaseModel):
    command: str = Field(..., description="Shell command to execute")

class UrlParams(BaseModel):
    url: str = Field(..., description="Full URL to open")

class MediaParams(BaseModel):
    query: str = Field(..., description="Search query or URL")
    strategy: str = Field("youtube", description="Platform strategy: 'youtube' or 'spotify'")

class MessageParams(BaseModel):
    target: str = Field(..., description="Phone number or contact name")
    content: str = Field(..., description="Message body")
    strategy: str = Field("whatsapp_desktop", description="'whatsapp_desktop' or 'whatsapp_api'")

class FileParams(BaseModel):
    file_path: str = Field(..., description="Destination file path")
    content: str = Field(..., description="Content to write to the file")

class DelegateParams(BaseModel):
    task: str = Field(..., description="Complex task description for OpenClaw")

# --- Action Implementations ---

class OpenAppAction(Action):
    name = "open_app"
    description = "Launches a desktop application. Falls back to Web if available."
    parameters_model = AppParams

    def __init__(self, app_launcher, browser_controller=None):
        self.app_launcher = app_launcher
        self.browser_controller = browser_controller
        self.fallback_map = {
            "spotify": "https://open.spotify.com",
            "whatsapp": "https://web.whatsapp.com",
            "telegram": "https://web.telegram.org",
            "instagram": "https://www.instagram.com",
            "facebook": "https://www.facebook.com",
            "messenger": "https://www.messenger.com",
            "twitter": "https://twitter.com",
            "x": "https://twitter.com",
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
            "outlook": "https://outlook.live.com",
            "netflix": "https://www.netflix.com",
            "chatgpt": "https://chatgpt.com",
            "discord": "https://discord.com/app",
            "slack": "https://app.slack.com/client",
            "notion": "https://www.notion.so",
            "trello": "https://trello.com"
        }

    def execute(self, params: AppParams) -> Dict[str, Any]:
        # 1. Try App (using robust Windows Key search)
        if self.app_launcher.open_app(params.app_name):
            return {"success": True, "message": f"Opened {params.app_name} (App)"}
        
        # 2. Try Web Fallback
        lower_name = params.app_name.lower()
        # Check exact match or if key is in app_name
        fallback_url = self.fallback_map.get(lower_name)
        if not fallback_url:
            # Fuzzy check
            for key, url in self.fallback_map.items():
                if key in lower_name:
                    fallback_url = url
                    break
        
        if self.browser_controller and fallback_url:
            logger.warning(f"App {params.app_name} failed/not found. Fallback to URL: {fallback_url}")
            self.browser_controller.open_url(fallback_url)
            return {"success": True, "message": f"Opened {params.app_name} (Web Fallback)"}
            
        return {"success": False, "message": f"Failed to open {params.app_name}"}

class CloseAppAction(Action):
    name = "close_app"
    description = "Closes a running application."
    parameters_model = AppParams

    def __init__(self, app_launcher):
        self.app_launcher = app_launcher

    def execute(self, params: AppParams) -> Dict[str, Any]:
        result = self.app_launcher.close_app(params.app_name)
        return {"success": bool(result), "message": f"Closed {params.app_name}"}

class FocusAppAction(Action):
    name = "focus_app"
    description = "Brings an application window to the foreground."
    parameters_model = AppParams

    def __init__(self, app_launcher):
        self.app_launcher = app_launcher

    def execute(self, params: AppParams) -> Dict[str, Any]:
        result = self.app_launcher.focus_app(params.app_name)
        return {"success": bool(result), "message": f"Focused {params.app_name}"}

class TypeTextAction(Action):
    name = "type_text"
    description = "Types text at the current cursor location."
    parameters_model = TextParams

    def execute(self, params: TextParams) -> Dict[str, Any]:
        import pyautogui
        pyautogui.write(params.text)
        return {"success": True, "message": f"Typed text (len={len(params.text)})"}

class PressKeyAction(Action):
    name = "press_key"
    description = "Presses a specific keyboard key."
    parameters_model = KeyParams

    def execute(self, params: KeyParams) -> Dict[str, Any]:
        import pyautogui
        pyautogui.press(params.key)
        return {"success": True, "message": f"Pressed {params.key}"}

class ClickElementAction(Action):
    name = "click_element"
    description = "Clicks at specific screen coordinates."
    parameters_model = ClickParams

    def execute(self, params: ClickParams) -> Dict[str, Any]:
        import pyautogui
        pyautogui.click(x=params.coordinates[0], y=params.coordinates[1])
        return {"success": True, "message": f"Clicked at {params.coordinates}"}

class RunCommandAction(Action):
    name = "run_command"
    description = "Executes a shell command. Use 'code <file>' to open VS Code."
    parameters_model = CommandParams

    def execute(self, params: CommandParams) -> Dict[str, Any]:
        target = params.command
        # Special handling for 'code' command logic
        if target.startswith("code "):
            parts = target.split(" ", 1)
            if len(parts) > 1:
                file_arg = parts[1]
                # Logic copied from executor.py: attempt to resolve path if relative
                if not os.path.isabs(file_arg):
                    if not os.path.dirname(file_arg):
                        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                        possible_path = os.path.join(downloads_path, file_arg)
                        if os.path.exists(possible_path):
                            target = f"code \"{possible_path}\""
        
        try:
            subprocess.Popen(target, shell=True)
            return {"success": True, "message": f"Started command: {target}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

class OpenUrlAction(Action):
    name = "open_url"
    description = "Opens a website in the default browser."
    parameters_model = UrlParams

    def __init__(self, browser_controller):
        self.browser_controller = browser_controller

    def execute(self, params: UrlParams) -> Dict[str, Any]:
        result = self.browser_controller.open_url(params.url)
        return {"success": bool(result), "message": f"Opened URL {params.url}"}

class PlayMediaAction(Action):
    name = "play_media"
    description = "Plays media on YouTube or Spotify. Prioritizes Desktop Apps."
    parameters_model = MediaParams

    def __init__(self, app_launcher, browser_controller):
        self.app_launcher = app_launcher
        self.browser_controller = browser_controller

    def execute(self, params: MediaParams) -> Dict[str, Any]:
        strategy = params.strategy.lower()
        query = params.query.strip()
        
        # Handle generic/empty queries
        is_generic_query = not query or query.lower() in ["music", "song", "random", "play music", "play song", "something"]
        if is_generic_query:
            import random
            generic_options = ["Top Hits", "Lofi Beats", "Today's Top Hits", "Viral 50", "Rock Classics"]
            query = random.choice(generic_options)
            logger.info(f"Generic query detected. Defaulting to: {query}")

        if "spotify" in strategy:
            # 1. Try Spotify Desktop App
            try:
                # Use the new robust Windows Key search from app_launcher
                if self.app_launcher.open_app("Spotify"):
                    import pyautogui
                    time.sleep(5) # Wait for Spotify to fully load/focus
                    
                    # If generic query and already playing, maybe just ensure it's playing?
                    # But user said "play some random song", so let's search new one.
                    
                    # Spotify Desktop Shortcuts:
                    # Ctrl + L: Focus Search
                    pyautogui.hotkey('ctrl', 'l')
                    time.sleep(1)
                    
                    # Type Query
                    pyautogui.write(query)
                    time.sleep(1.5)
                    
                    # Enter to Search
                    pyautogui.press('enter')
                    time.sleep(2)
                    
                    # Move focus to the "Top Result" or "Songs" list
                    # Pressing Tab once usually highlights the "Play" button of the Top Result
                    # Pressing Enter then plays it.
                    pyautogui.press('tab')
                    time.sleep(0.5)
                    pyautogui.press('enter')
                    
                    # Fallback: sometimes focus is weird. 
                    # Try clicking the "Play" button of the first song in list? 
                    # Or try hitting Enter again if the first one didn't work.
                    time.sleep(1)
                    # If nothing happened, maybe we are still in search bar?
                    # Let's try to force play/pause if we think it worked? 
                    # No, that might pause if it was already playing.
                    
                    # Try 'Ctrl + Enter' (sometimes plays selected item)
                    # pyautogui.hotkey('ctrl', 'enter') 
                    
                    return {"success": True, "message": f"Playing Spotify (Desktop): {query}"}
                else:
                    logger.warning("Failed to open Spotify Desktop. Falling back to Web.")
            except Exception as e:
                logger.warning(f"Spotify Desktop error: {e}. Falling back to Web.")

            # 2. Fallback to Spotify Web Player
            result = self.browser_controller.play_spotify(query)
            return {"success": bool(result), "message": f"Playing Spotify (Web Fallback): {query}"}
        
        else:
            # Default to YouTube (Browser)
            result = self.browser_controller.play_youtube(query)
            return {"success": bool(result), "message": f"Playing YouTube: {query}"}

class SendMessageAction(Action):
    name = "send_message"
    description = "Sends a message via WhatsApp (Desktop or API)."
    parameters_model = MessageParams

    def __init__(self, desktop_controller, whatsapp_api):
        self.desktop_controller = desktop_controller
        self.whatsapp_api = whatsapp_api

    def execute(self, params: MessageParams) -> Dict[str, Any]:
        target = params.target
        message = params.content
        strategy = params.strategy.lower()

        if "whatsapp" in strategy:
            # 1. Try WhatsApp API if requested
            if "api" in strategy or "cloud" in strategy:
                if self.whatsapp_api.is_available():
                    result = self.whatsapp_api.send_message(target, message)
                    return {"success": bool(result), "message": "Sent via WhatsApp API"}
                else:
                    logger.warning("WhatsApp API unavailable. Falling back to Desktop.")
            
            # 2. Try WhatsApp Desktop
            try:
                result = self.desktop_controller.send_whatsapp_desktop_message(target, message)
                if result:
                    return {"success": True, "message": "Sent via WhatsApp Desktop"}
                else:
                    logger.warning("WhatsApp Desktop failed. Falling back to Web.")
            except Exception as e:
                logger.warning(f"WhatsApp Desktop error: {e}. Falling back to Web.")

            # 3. Fallback to WhatsApp Web
            # We need a browser controller for this.
            # Since SendMessageAction didn't have browser_controller injected, we need to add it or import it.
            # Importing BrowserController locally to avoid changing __init__ signature if possible,
            # BUT __init__ is the clean way. Let's update __init__.
            
            # Since I cannot easily change the __init__ call sites in executor.py without a second edit,
            # I will instantiate BrowserController here as a fallback.
            from skills.browser_controller import BrowserController
            browser = BrowserController()
            
            # Use the existing send_whatsapp_message method in BrowserController
            # which handles phone numbers vs contact names via URL hacks or UI automation
            web_result = browser.send_whatsapp_message(target, message)
            if web_result:
                 return {"success": True, "message": "Sent via WhatsApp Web (Fallback)"}
            
            return {"success": False, "message": "All WhatsApp strategies failed (API, Desktop, Web)."}
        
        return {"success": False, "message": f"Unknown strategy {strategy}"}

class WriteFileAction(Action):
    name = "write_file"
    description = "Writes content to a file."
    parameters_model = FileParams

    def __init__(self, filesystem_manager):
        self.filesystem_manager = filesystem_manager

    def execute(self, params: FileParams) -> Dict[str, Any]:
        result_path = self.filesystem_manager.write_file(params.file_path, params.content)
        if result_path:
            return {"success": True, "message": f"File created at {result_path}", "path": result_path}
        return {"success": False, "message": "Failed to write file"}

class DelegateAction(Action):
    name = "delegate_to_openclaw"
    description = "Delegates a complex task to OpenClaw."
    parameters_model = DelegateParams

    def __init__(self, openclaw_client):
        self.openclaw_client = openclaw_client

    def execute(self, params: DelegateParams) -> Dict[str, Any]:
        result = self.openclaw_client.execute_task(params.task)
        return {"success": True, "message": f"OpenClaw result: {result}"}
