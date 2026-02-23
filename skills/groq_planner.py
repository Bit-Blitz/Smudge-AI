import os
import yaml
from groq import Groq
import json
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger import logger
from skills.actions.registry import ActionRegistry

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
            
        # Sub-Planning State
        self.current_goal = None
        self.sub_plan = []
        
        # Load Action Schemas from Registry
        self.registry = ActionRegistry()
        # We need to register actions here or ensure they are registered. 
        # Since Registry is currently empty when instantiated new, we need a way to share the registry or register them.
        # However, the implementations are in a separate file. 
        # A better approach is to have a factory or a module that pre-registers them, 
        # OR just import them and register them here similar to Executor.
        
        # To avoid code duplication with Executor, we should probably have a 'default_registry' or 'register_all_actions' helper.
        # For now, let's keep it simple and register them here too, or just use the classes directly if we don't want to duplicate registration logic.
        # But the goal is to use Registry.
        
        from skills.actions.implementations import (
            OpenAppAction, CloseAppAction, FocusAppAction, TypeTextAction, PressKeyAction,
            ClickElementAction, RunCommandAction, OpenUrlAction, PlayMediaAction,
            SendMessageAction, WriteFileAction, DelegateAction
        )
        
        # Registering actions to get their schemas
        # Note: We are instantiating them with None/Mock services because we only need schemas here.
        # Ideally, to_schema is a class method, so we don't need instances.
        # The registry.get_all_schemas() iterates over instances in the current implementation of registry.py?
        # Let's check registry.py again. 
        # "return [action.to_schema() for action in self._actions.values()]"
        # Yes, it uses instances.
        # But Action.to_schema is a classmethod.
        
        # Let's update Registry to support class-based registration or just use the classes directly for now to avoid complex dependency injection here.
        # Actually, since to_schema is a class method, we can just list the classes.
        
        self.action_classes = [
            OpenAppAction, CloseAppAction, FocusAppAction, TypeTextAction, PressKeyAction,
            ClickElementAction, RunCommandAction, OpenUrlAction, PlayMediaAction,
            SendMessageAction, WriteFileAction, DelegateAction
        ]
        self.action_schemas = [cls.to_schema() for cls in self.action_classes]

    def _decompose_goal(self, goal):
        """Breaks down a high-level goal into logical sub-steps using LLM."""
        logger.info(f"Decomposing high-level goal: {goal}")
        prompt = f"""
GOAL: {goal}

INSTRUCTIONS:
You are a senior task planner. Break down the user's goal into a logical sequence of high-level steps.
Think about the likely workflow required.

Examples:
- "Open TTDE notes" -> ["Open Browser", "Go to classroom.google.com", "Find and Click 'TTDE' class", "Click 'Classwork' tab", "Open a PDF attachment"]
- "Email John about the meeting" -> ["Open Email Client", "Compose New Email", "Type Subject 'Meeting'", "Type Body", "Send"]

Return ONLY a valid JSON list of strings.
Example: ["Step 1", "Step 2", "Step 3"]
"""
        try:
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.config['llm']['groq']['planner_model'],
                response_format={"type": "json_object"}
            )
            # The model might return {"steps": [...]} or just [...] depending on training
            # Let's ask for an object to be safe
            content = completion.choices[0].message.content
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif "steps" in data:
                return data["steps"]
            else:
                # Fallback
                return [goal]
        except Exception as e:
            logger.error(f"Decomposition failed: {e}")
            return [goal] # Fallback to single step

    def plan(self, goal, current_state, history=None):
        if not self.client:
            logger.info("Generating mock plan (no API key)...")
            return self._mock_plan(goal, current_state)

        # --- SUB-PLANNING LOGIC ---
        # If the goal has changed significantly, reset the sub-plan
        if goal != self.current_goal:
            self.current_goal = goal
            # Heuristic: If goal is short (< 5 words) and ambiguous, try to decompose
            # Or if it contains keywords like "notes", "project", "research"
            if len(goal.split()) < 10 or "notes" in goal.lower() or "class" in goal.lower():
                self.sub_plan = self._decompose_goal(goal)
                logger.info(f"Generated Sub-Plan: {self.sub_plan}")
            else:
                self.sub_plan = [goal]

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

        # Inject Sub-Plan context
        sub_plan_str = "STRATEGIC WORKFLOW (Follow this guide):\n"
        for i, step in enumerate(self.sub_plan):
            sub_plan_str += f"{i+1}. {step}\n"

        # Serialize schemas for prompt
        schemas_str = json.dumps(self.action_schemas, indent=2)

        prompt = f"""
GOAL: {goal}

{sub_plan_str}

{history_str}

CURRENT STATE:
{json.dumps(current_state, indent=2)}

AVAILABLE ACTIONS (Strict Schema):
{schemas_str}

INSTRUCTIONS:
You are an autonomous desktop agent. Based on the goal, previous actions, and current state, determine the next best action.
CRITICAL: If the goal has been fully achieved based on the PREVIOUS ACTIONS (e.g., message sent, file written), you MUST return action "done". DO NOT REPEAT COMPLETED ACTIONS.

You MUST return a valid JSON object matching this structure:
{{
  "action": "action_name_from_schema",
  "parameters": {{
    "param_name": "value"
  }},
  "thought": "Reasoning for this action",
  "confidence": 0.0-1.0
}}

Example:
{{
  "action": "open_app",
  "parameters": {{
    "app_name": "Notepad"
  }},
  "thought": "Opening Notepad to write the file.",
  "confidence": 0.95
}}

Usage Notes:
- write_file: PREFER THIS for "write code" requests.
- run_command: Use "code <filename>" to open VS Code.
- done: When goal is complete. Use action "done" with parameters {{}}.

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