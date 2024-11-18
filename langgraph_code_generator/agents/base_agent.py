from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage
import openai
import logging
import os
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

# Define model constants from environment variables
DEFAULT_MODEL = os.getenv("OPENROUTER_LARGE_MODEL", "anthropic/claude-3-sonnet-20240229")
SMALL_MODEL = os.getenv("OPENROUTER_SMALL_MODEL", "anthropic/claude-3-haiku-20240307")

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class BaseAgent(ABC):
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model_name = model_name
        
    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main functionality"""
        pass
    
    def _invoke_model(self, messages: list) -> str:
        """Helper method to invoke the model with proper error handling"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": m.type, "content": m.content} for m in messages],
                max_tokens=4096,
                temperature=0.1
            )
            logger.debug(f"Model response: {response.choices[0].message.content}")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error invoking model: {e}")
            raise

    def parse_xml(self, xml_content: str) -> ET.Element:
        """Parse XML content into an ElementTree Element"""
        try:
            root = ET.fromstring(xml_content)
            logger.debug("XML parsed successfully.")
            return root
        except ET.ParseError as e:
            logger.error(f"Error parsing XML: {e}")
            raise

    def generate_xml(self, root: ET.Element) -> str:
        """Generate XML string from an ElementTree Element"""
        try:
            xml_str = ET.tostring(root, encoding='unicode')
            logger.debug("XML generated successfully.")
            return xml_str
        except Exception as e:
            logger.error(f"Error generating XML: {e}")
            raise

    def update_state(self, state: Dict[str, Any], key: str, value: Any) -> None:
        """Utility method to update the state dictionary"""
        state[key] = value
        logger.debug(f"State updated: {key} = {value}")

    def get_from_state(self, state: Dict[str, Any], key: str, default: Optional[Any] = None) -> Any:
        """Utility method to retrieve a value from the state dictionary"""
        return state.get(key, default)