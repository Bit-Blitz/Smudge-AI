import os
from google import genai
import pyautogui
from PIL import Image
import json
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger import logger

class VisionFallback:
    def __init__(self, config_path="d:/Ceaser-AI/openclaw/config.yaml"):
        with open(config_path, 'r') as f:
            import yaml
            self.config = yaml.safe_load(f)
        
        self.api_key = os.getenv("GEMINI_API_KEY") or self.config['llm']['gemini']['api_key']
        if self.api_key == "${GEMINI_API_KEY}":
            logger.warning("GEMINI_API_KEY not set. Vision fallback disabled.")
            self.client = None
            self.model_name = None
        else:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = self.config['llm']['gemini']['vision_model']

    def fallback(self, goal, current_state, image_path=None):
        if not self.client:
            logger.warning("Vision fallback triggered but not configured.")
            return {"action": "wait", "reason": "vision_not_configured"}

        logger.info("Engaging Vision Fallback...")
        
        # Use provided image or capture screenshot
        if image_path:
            logger.info(f"Using provided image: {image_path}")
            target_image_path = image_path
        else:
            target_image_path = "d:/Ceaser-AI/logs/vision_capture.png"
            try:
                screenshot = pyautogui.screenshot()
                screenshot.save(target_image_path)
            except Exception as e:
                logger.error(f"Failed to capture screenshot: {e}")
                return {"error": "screenshot_failed"}
        
        prompt = f"""
GOAL: {goal}

The current structured state is:
{json.dumps(current_state, indent=2)}

The execution of the last plan FAILED or is stuck.
Analyze the screenshot to determine what went wrong and suggest a corrective action.
Return a JSON object with the correction plan (action, target, etc.) or "wait".
"""
        try:
            # Load image
            if image_path:
                img = Image.open(image_path)
            else:
                img = Image.open(target_image_path)
                
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img]
            )
            text = response.text
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                logger.warning(f"Could not parse JSON from Vision Fallback: {text}")
                return {"action": "wait", "reason": "parse_error"}
                
        except Exception as e:
            logger.error(f"Vision Fallback error: {e}")
            return {"error": str(e)}

    def analyze_screen(self, query="Describe the current screen state and active elements."):
        """Captures screen and asks Gemini to describe it."""
        if not self.client:
            return "Vision model not configured."
            
        target_image_path = "d:/Ceaser-AI/logs/vision_capture_analysis.png"
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(target_image_path), exist_ok=True)
            
            screenshot = pyautogui.screenshot()
            screenshot.save(target_image_path)
            img = Image.open(target_image_path)
            
            logger.info(f"Analyzing screen with query: {query}")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[query, img]
            )
            return response.text
        except Exception as e:
            logger.error(f"Screen analysis failed: {e}")
            return f"Error analyzing screen: {e}"

if __name__ == "__main__":
    pass
