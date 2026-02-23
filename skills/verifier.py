import time
import os
import sys
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger import logger
from skills.structured_perception import StructuredPerception

class Verifier:
    def __init__(self):
        self.perception = StructuredPerception()

    def verify(self, plan, initial_state, final_state):
        """Verifies if the plan execution was successful."""
        logger.info(f"Verifying plan: {plan}")
        
        action = plan.get("action")
        
        # Extract target from either legacy or new schema structure
        target = plan.get("target")
        parameters = plan.get("parameters", {})
        
        if not target and parameters:
            # Map schema parameters to verification target
            if action in ["open_app", "close_app", "focus_app"]:
                target = parameters.get("app_name")
            elif action == "type_text":
                target = parameters.get("text")
            elif action == "press_key":
                target = parameters.get("key")
            elif action == "run_command":
                target = parameters.get("command")
            elif action == "open_url":
                target = parameters.get("url")
        
        if not action:
            return False
        
        if not target and action not in ["click_element", "press_key", "type_text", "done", "wait"]:
             # Some actions might not have a clear 'target' string to verify against title
             pass

        if action == "open_app":
            if not target:
                logger.warning("Verification skipped: No target app name found.")
                return True # Optimistic

            # Check if target app is in open windows or focused app
            open_windows = final_state.get("open_windows", [])
            # ... (rest of logic)
            for win in open_windows:
                if target.lower() in win["title"].lower():
                    logger.info(f"Verification successful: {target} is open.")
                    return True
            
            focused_app = final_state.get("system", {}).get("focused_app", "")
            if target.lower() in focused_app.lower():
                logger.info(f"Verification successful: {target} is focused.")
                return True
                
            logger.warning(f"Verification failed: {target} not found in open windows or focused app.")
            return False
            
        elif action == "close_app":
            # Check if target app is NOT in open windows
            open_windows = final_state.get("open_windows", [])
            for win in open_windows:
                if target.lower() in win["title"].lower():
                    logger.warning(f"Verification failed: {target} is still open.")
                    return False
            logger.info(f"Verification successful: {target} is closed.")
            return True
            
        elif action == "type_text":
            # Hard to verify without vision or content extraction
            logger.info("Verification for type_text assumed successful (no feedback loop implemented).")
            return True
            
        # Default assume success for now unless explicit failure check implemented
        return True

if __name__ == "__main__":
    verifier = Verifier()
    # Test logic
