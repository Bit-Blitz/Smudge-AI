import webbrowser
import time
import urllib.parse
import urllib.request
import re
import threading
import uiautomation as auto
from utils.logger import logger

class BrowserController:
    def __init__(self):
        pass

    def open_url(self, url):
        """Opens a URL in the default browser."""
        logger.info(f"Opening URL: {url}")
        try:
            webbrowser.open(url)
            time.sleep(2) # Wait for browser to launch
            return True
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return False

    def play_youtube(self, query):
        """Searches YouTube for the query and plays the first video."""
        logger.info(f"Searching YouTube for: {query}")
        try:
            # Encode query for URL
            query_string = urllib.parse.urlencode({"search_query": query})
            search_url = f"https://www.youtube.com/results?{query_string}"
            
            # Fetch search results page
            with urllib.request.urlopen(search_url) as response:
                html = response.read().decode()
                
            # Extract first video ID using regex
            # Look for videoId":"VIDEO_ID" pattern
            video_ids = re.findall(r'"videoId":"([^"]+)"', html)
            
            if video_ids:
                first_video_id = video_ids[0]
                video_url = f"https://www.youtube.com/watch?v={first_video_id}"
                logger.info(f"Found video ID: {first_video_id}, opening: {video_url}")
                self.open_url(video_url)
                
                # Launch ad skipper in background to avoid blocking main execution flow too long
                # but ensure it runs
                threading.Thread(target=self.skip_youtube_ads, daemon=True).start()
                return True
            else:
                logger.warning("No video IDs found in search results. Opening search page instead.")
                return self.open_url(search_url)
                
        except Exception as e:
            logger.error(f"Failed to play YouTube video for query '{query}': {e}")
            # Fallback to search page
            fallback_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            return self.open_url(fallback_url)

    def skip_youtube_ads(self):
        """
        Monitors for 'Skip Ad' button on YouTube and clicks it if found.
        Uses UIAutomation to search for various labels like "Skip Ad", "Skip Ads", etc.
        """
        logger.info("Monitoring for YouTube ads...")
        start_time = time.time()
        max_duration = 45 # Wait up to 45 seconds (some ads are unskippable for 15s+)
        
        try:
            # Get the current foreground window (likely the browser) to scope the search
            # This is much faster than searching the entire desktop
            browser_window = auto.GetForegroundControl()
            if not browser_window:
                logger.warning("No foreground window found for ad skipping.")
                return

            while time.time() - start_time < max_duration:
                # Search for ANY control with "Skip Ad" in the name (case-insensitive)
                # Use FindFirst instead of GetFirstChildControl for depth control
                skip_button = browser_window.FindFirst(
                    auto.TreeScope.Descendants,
                    lambda c, d: isinstance(c.Name, str) and "skip" in c.Name.lower() and "ad" in c.Name.lower()
                )
                
                if skip_button and skip_button.Exists(0, 0):
                    logger.info(f"Ad detected! Found control '{skip_button.Name}'. Clicking...")
                    
                    # PRIORITY 1: Try Invoke Pattern (Does not move mouse, works in background)
                    try:
                        invoke_pattern = skip_button.GetInvokePattern()
                        if invoke_pattern:
                            invoke_pattern.Invoke()
                            logger.info("Ad skipped via Invoke Pattern (Silent).")
                            return
                    except Exception as e:
                        logger.debug(f"Invoke Pattern failed: {e}")

                    # PRIORITY 2: Try Legacy IAccessible Pattern (Does default action, usually click)
                    try:
                        legacy_pattern = skip_button.GetLegacyIAccessiblePattern()
                        if legacy_pattern and legacy_pattern.DefaultAction:
                            legacy_pattern.DoDefaultAction()
                            logger.info("Ad skipped via Legacy Pattern (Silent).")
                            return
                    except Exception as e:
                        logger.debug(f"Legacy Pattern failed: {e}")

                    # PRIORITY 3: Standard Click (Moves mouse)
                    # Only do this if we are ALREADY in the browser to avoid stealing focus from another app
                    if browser_window.HasKeyboardFocus:
                         try:
                            skip_button.Click(simulateMove=False) # Try click without moving mouse if possible
                            logger.info("Ad skipped via Standard Click.")
                            return
                         except Exception as e:
                            logger.warning(f"Standard Click failed: {e}")
                    else:
                         logger.info("Skipping physical click because browser is not focused (avoiding interruption).")
                         # We found the ad but couldn't silently skip it. 
                         # Better to do nothing than to steal focus while user is typing.
                         
                    return
                
                # Check every 2 seconds to be less CPU intensive
                time.sleep(2)
                
                # Refresh window handle in case user switched tabs/windows?
                # Actually, better to re-acquire foreground if we lost it?
                # For now, let's just re-check if we still have a valid window
                if not browser_window.Exists(0, 0):
                     browser_window = auto.GetForegroundControl()
                
            logger.info("No skippable ad detected within timeout.")
            
        except Exception as e:
            logger.error(f"Error while trying to skip ads: {e}")

    def play_spotify(self, query):
        """Searches Spotify for the query and opens the web player."""
        logger.info(f"Searching Spotify for: {query}")
        try:
            # Use Spotify's web player search URL
            # Note: User must be logged in for seamless playback
            search_url = f"https://open.spotify.com/search/{urllib.parse.quote(query)}"
            return self.open_url(search_url)
        except Exception as e:
            logger.error(f"Failed to play Spotify for query '{query}': {e}")
            return False

    def send_whatsapp_message(self, target, message):
        """
        Opens WhatsApp Web to send a message.
        If target is a phone number (digits), uses direct link.
        If target is a name, searches for the contact.
        """
        logger.info(f"Sending WhatsApp message to {target} via Web")
        try:
            # Check if target is a phone number (mostly digits)
            clean_phone = "".join(filter(str.isdigit, str(target)))
            is_phone_number = len(clean_phone) >= 7  # Minimal length for a phone number
            
            encoded_message = urllib.parse.quote(message)
            
            if is_phone_number:
                # Use Direct Link API for phone numbers
                url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_message}"
                self.open_url(url)
                
                # Wait for page load and send button
                time.sleep(15)
                
                # Press Enter to send (the text is already pre-filled by the URL)
                import pyautogui
                pyautogui.press('enter')
                return True
            else:
                # Use Search Link for saved contact names
                logger.info(f"Target '{target}' appears to be a name. Opening WhatsApp Web main page.")
                self.open_url("https://web.whatsapp.com/")
                
                import pyautogui
                
                # Wait for WhatsApp Web to load
                time.sleep(15) 
                
                # Focus the search box (Ctrl + Alt + / is the shortcut)
                pyautogui.hotkey('ctrl', 'alt', '/')
                time.sleep(2) 
                
                # Type the name
                pyautogui.write(target)
                time.sleep(3) # Wait for search results
                
                # Select contact
                pyautogui.press('enter') 
                time.sleep(2) 
                
                # Type message
                pyautogui.write(message)
                time.sleep(1)
                pyautogui.press('enter') # Send
                
                return True

        except Exception as e:
            logger.error(f"Failed to send WhatsApp message via Web: {e}")
            return False

        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False

if __name__ == "__main__":
    bc = BrowserController()
    # bc.open_url("https://www.youtube.com")
    # bc.play_youtube("lofi hip hop")
    # bc.play_spotify("classical music")
    # bc.send_whatsapp_message("1234567890", "Hello from Aegis!")
