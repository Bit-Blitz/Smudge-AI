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
from skills.actions.registry import ActionRegistry
from skills.actions.implementations import (
    OpenAppAction, CloseAppAction, FocusAppAction, TypeTextAction, PressKeyAction,
    ClickElementAction, RunCommandAction, OpenUrlAction, PlayMediaAction,
    SendMessageAction, WriteFileAction, DelegateAction
)

class Executor:
    def __init__(self):
        # Initialize Services
        self.app_launcher = AppLauncher()
        self.perception = StructuredPerception()
        self.browser_controller = BrowserController()
        self.filesystem_manager = FilesystemManager()
        self.openclaw = OpenClawClient()
        self.desktop_controller = DesktopAppController()
        self.whatsapp_api = WhatsAppAPIClient()

        # Initialize Registry
        self.registry = ActionRegistry()
        self._register_actions()

    def _register_actions(self):
        """Registers all available actions with their dependencies."""
        self.registry.register(OpenAppAction(self.app_launcher, self.browser_controller))
        self.registry.register(CloseAppAction(self.app_launcher))
        self.registry.register(FocusAppAction(self.app_launcher))
        self.registry.register(TypeTextAction())
        self.registry.register(PressKeyAction())
        self.registry.register(ClickElementAction())
        self.registry.register(RunCommandAction())
        self.registry.register(OpenUrlAction(self.browser_controller))
        self.registry.register(PlayMediaAction(self.app_launcher, self.browser_controller))
        self.registry.register(SendMessageAction(self.desktop_controller, self.whatsapp_api))
        self.registry.register(WriteFileAction(self.filesystem_manager))
        self.registry.register(DelegateAction(self.openclaw))

    def execute_plan(self, plan):
        """Executes the given plan using the Action Registry."""
        logger.info(f"Executing plan: {plan}")
        
        action_name = plan.get("action")
        if not action_name:
            logger.error("No action specified in plan.")
            return False

        action = self.registry.get_action(action_name)
        if not action:
            logger.error(f"Unknown action: {action_name}")
            return False

        # --- Compatibility Layer: Map Legacy Params to Schema ---
        try:
            params_dict = self._map_legacy_params(action_name, plan)
            
            # Validate with Pydantic
            # This ensures that even if the LLM hallucinates parameters, 
            # we catch it here before execution logic starts.
            validated_params = action.parameters_model(**params_dict)
            
            # Execute
            result = action.execute(validated_params)
            
            # Handle result logging
            if isinstance(result, dict):
                if not result.get("success"):
                    logger.warning(f"Action {action_name} failed: {result.get('message')}")
                    return False
                else:
                    # Return the full result dict so upstream can see messages/paths
                    return result
            
            return result

        except Exception as e:
            logger.error(f"Error executing action {action_name}: {e}")
            # Self-healing logic
            self._heal_error(e, action_name, plan.get("target"), plan)
            return False

    def _map_legacy_params(self, action_name, plan):
        """Maps legacy flat plan structure to Pydantic schema structure."""
        # If 'parameters' key exists, assume it's already structured
        if "parameters" in plan:
            return plan["parameters"]
            
        # Legacy mapping
        target = plan.get("target")
        strategy = plan.get("strategy")
        content = plan.get("content")
        coordinates = plan.get("coordinates")

        if action_name in ["open_app", "close_app", "focus_app"]:
            return {"app_name": target}
        elif action_name == "type_text":
            return {"text": target}
        elif action_name == "press_key":
            return {"key": target}
        elif action_name == "click_element":
            return {"coordinates": coordinates}
        elif action_name == "run_command":
            return {"command": target}
        elif action_name == "open_url":
            return {"url": target}
        elif action_name == "play_media":
            return {"query": target, "strategy": strategy or "youtube"}
        elif action_name == "send_message":
            return {"target": target, "content": content, "strategy": strategy or "whatsapp_desktop"}
        elif action_name == "write_file":
            return {"file_path": target, "content": content}
        elif action_name == "delegate_to_openclaw":
            return {"task": target}
            
        return {} # Should fail validation if params are missing

    def _heal_error(self, error, action, target, plan):
        """
        Uses the Planner (LLM) to analyze the traceback and suggest a fix.
        """
        from skills.groq_planner import GroqPlanner
        planner = GroqPlanner() # Re-instantiate to avoid circular deps if any
        
        goal = f"Fix error '{str(error)}' when executing action '{action}' on target '{target}'"
        current_state = {"error": str(error), "failed_plan": plan}
        
        # We ask the planner for a new plan given the error
        # This is a simplified version of self-healing (retry with different params)
        return None

if __name__ == "__main__":
    executor = Executor()
    # Test new structure with legacy format
    result = executor.execute_plan({"action": "open_app", "target": "Notepad"})
    print(f"Execution Result: {result}")
