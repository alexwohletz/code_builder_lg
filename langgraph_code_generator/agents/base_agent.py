from abc import ABC, abstractmethod
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
import logging
import os

# Define model constants from environment variables
DEFAULT_MODEL = os.getenv("ANTHROPIC_LARGE_MODEL", "claude-3-5-sonnet-20241022")
ANTHROPIC_SMALL_MODEL = os.getenv("ANTHROPIC_SMALL_MODEL", "claude-3-5-haiku-20241022")

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model = ChatAnthropic(
            model=model_name,
            max_tokens=4096,  # Increase max output tokens
            temperature=0.1   # Lower temperature for more consistent outputs
        )
        
    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main functionality"""
        pass
    
    def _invoke_model(self, messages: list) -> str:
        """Helper method to invoke the model with proper error handling"""
        try:
            response = self.model.invoke(
                messages,
                max_tokens=4096,  # Ensure it's set per-request too
            )
            return response.content
        except Exception as e:
            logger.error(f"Error invoking model: {e}")
            raise
