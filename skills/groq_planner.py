import os
import yaml
from groq import Groq
import json
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger import logger

class GroqPlanner:
    def __init__(self, config_path="d:/Ceaser-AI/openclaw/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.api_key = os.getenv("GROQ_API_KEY") or self.config['llm']['groq']['api_key']
        if self.api_key == "${GROQ_API_KEY}":
            logger.warning("GROQ_API_KEY not set in environment or config. Using mock mode.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)

    def plan(self, goal, current_state, history=None):
        if not self.client:
            logger.info("Generating mock plan (no API key)...")
            return self._mock_plan(goal, current_state)

        logger.info(f"Planning for goal: {goal}")
        
        history_str = ""
        if history:
            history_str = "PREVIOUS ACTIONS:\n"
            for i, step in enumerate(history[-5:]): # Last 5 steps
                # FIX: Handle inconsistent history structure
                plan = step.get("plan") or step.get("log", {}).get("plan", {})
                action = plan.get("action", "unknown")
                status = step.get("status", "unknown")
                history_str += f"{i+1}. {action} -> {status}\n"
        
        # Check history for duplicate actions to prevent loops
        if history:
             last_step = history[-1]
             last_plan = last_step.get("plan") or last_step.get("log", {}).get("plan", {})
             last_action = last_plan.get("action")
             last_status = last_step.get("status")
             
             if last_status == "success" and last_action != "done":
                  logger.info("Last action successful. Checking if goal is complete...")
                  # Append instruction to strongly encourage finishing if it looks like we just did the main task
                  history_str += "\nNOTE: The last action was successful. If this completed the user's request, you MUST output {'action': 'done'}."

        prompt = f"""
GOAL: {goal}

{history_str}

CURRENT STATE:
{json.dumps(current_state, indent=2)}

INSTRUCTIONS:
You are an autonomous desktop agent. based on the goal, previous actions, and current state, determine the next best action.
CRITICAL: If the goal has been fully achieved based on the PREVIOUS ACTIONS (e.g., message sent, file written), you MUST return action "done". DO NOT REPEAT COMPLETED ACTIONS.

Return ONLY a valid JSON object with the following structure:
{{
  "action": "action_name",
  "target": "target_name_or_value",
  "content": "file_content_if_writing_file",
  "strategy": "strategy_name",
  "confidence": 0.0-1.0
}}

Available actions: open_app, close_app, focus_app, type_text, press_key, click_element, run_command, open_url, write_file, play_media, send_message, delegate_to_openclaw, done.

Specific Usage Notes:
- done: use when the goal is complete. target can be "Goal achieved".
- write_file: PREFER THIS for "write code" or "create program" requests. Create the file first, then open it.
- run_command: use for executing terminal commands. To open a file in VS Code, use "code <filename>".
- play_media: set 'target' to query. set 'strategy' to 'youtube' or 'spotify'.
- send_message: set 'target' to phone number or name. set 'strategy' to 'whatsapp_desktop' (default) or 'whatsapp_api' (requires keys).
- delegate_to_openclaw: use for complex multi-step reasoning or if requested explicitly.

BEST PRACTICES:
- If user says "Open VS Code and write a program", do NOT use type_text. Instead:
  1. write_file (save the code to disk first)
  2. run_command "code <filename>" (this opens VS Code with the file)
  3. done
- If user says "search for X", use play_media or open_url.

"""
        
        # Define fallback models in order of preference
        models_to_try = [
            self.config['llm']['groq']['planner_model'], # Primary (e.g. llama-3.3-70b)
            "llama-3.1-70b-versatile",                   # Backup 1 (High reasoning)
            "llama-3.1-8b-instant",                      # Backup 2 (Super fast)
            "gemma2-9b-it"                               # Backup 3 (Google's model on Groq)
        ]

        for model in models_to_try:
            try:
                logger.info(f"Attempting planning with model: {model}")
                completion = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful desktop assistant that outputs structured JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    model=model,
                    response_format={"type": "json_object"}
                )
                
                response_content = completion.choices[0].message.content
                logger.debug(f"Planner response: {response_content}")
                return json.loads(response_content)
                
            except Exception as e:
                # Check for Rate Limit Error (429)
                error_msg = str(e).lower()
                if "429" in error_msg or "rate limit" in error_msg:
                    logger.warning(f"Rate limit hit for model {model}. Switching to next available model...")
                    continue # Try next model
                else:
                    logger.error(f"Error during planning with {model}: {e}")
                    # If it's not a rate limit (e.g. auth error, bad request), we might still want to try another model 
                    # OR fail fast. For robustness, let's try the next one if it's a server error.
                    continue

        logger.error("All models failed or rate limited.")
        return {"action": "wait", "target": "Rate limit fallback failed"}

    def _mock_plan(self, goal, current_state):
        # Simple heuristic fallback for testing without API key
        goal_lower = goal.lower()
        if "chrome" in goal_lower:
            return {"action": "open_app", "target": "Chrome", "strategy": "search", "confidence": 0.9}
        elif "notepad" in goal_lower:
            return {"action": "open_app", "target": "Notepad", "strategy": "search", "confidence": 0.9}
        elif "type" in goal_lower:
            return {"action": "type_text", "target": "Hello World", "strategy": "direct", "confidence": 0.8}
        else:
            return {"action": "unknown", "target": None, "strategy": "none", "confidence": 0.0}

if __name__ == "__main__":
    planner = GroqPlanner()
    print(planner.plan("Open Chrome", {}))