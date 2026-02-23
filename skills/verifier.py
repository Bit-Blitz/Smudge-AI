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
        target = plan.get("target")
        
        if not action:
            return False
        
        if action == "open_app":
            # Check if target app is in open windows or focused app
            open_windows = final_state.get("open_windows", [])
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
