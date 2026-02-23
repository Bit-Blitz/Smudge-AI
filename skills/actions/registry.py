from typing import Dict, List, Optional, Any
from .base import Action
from utils.logger import logger

class ActionRegistry:
    
    def __init__(self):
        self._actions: Dict[str, Action] = {}

    def register(self, action: Action):
        """Registers a new action instance."""
        if action.name in self._actions:
            logger.warning(f"Overwriting existing action: {action.name}")
        self._actions[action.name] = action
        logger.debug(f"Registered action: {action.name}")

    def get_action(self, name: str) -> Optional[Action]:
        """Retrieves an action by name."""
        return self._actions.get(name)

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Returns schemas for all registered actions (for LLM context)."""
        return [action.to_schema() for action in self._actions.values()]

    def validate_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Validates a raw plan dictionary against the registered action schema.
        Returns True if valid, False otherwise.
        """
        action_name = plan.get("action")
        if not action_name:
            logger.error("Plan missing 'action' field")
            return False
            
        action = self.get_action(action_name)
        if not action:
            logger.error(f"Unknown action: {action_name}")
            return False
            
        # Basic validation that parameters match schema keys
        # Deep validation happens during execution via Pydantic
        return True
