from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Type

class Action(ABC):
    """
    Abstract base class for all actions.
    Enforces strict typing and self-documentation.
    """
    name: str
    description: str
    parameters_model: Type[BaseModel]

    @classmethod
    def to_schema(cls) -> Dict[str, Any]:
        """Returns the JSON schema for this action (for LLM context)."""
        return {
            "name": cls.name,
            "description": cls.description,
            "parameters": cls.parameters_model.model_json_schema()
        }

    @abstractmethod
    def execute(self, params: BaseModel) -> Dict[str, Any]:
        """
        Executes the action with validated parameters.
        Returns a dictionary with 'success' (bool) and 'message' (str).
        """
        pass
