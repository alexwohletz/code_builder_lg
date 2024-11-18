from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from langchain_core.messages import HumanMessage
import openai
import logging
import os
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice, ChatCompletionMessage

load_dotenv()

# Define model constants from environment variables
DEFAULT_MODEL = os.getenv("OPENROUTER_LARGE_MODEL", "anthropic/claude-3-sonnet-20240229")
SMALL_MODEL = os.getenv("OPENROUTER_SMALL_MODEL", "anthropic/claude-3-haiku-20240307")

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class BaseAgent(ABC):
    def __init__(self, model_name: str = DEFAULT_MODEL):
        # Check for required environment variables
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")
        
        # Debug environment variables
        logger.debug(f"Available models - DEFAULT: {DEFAULT_MODEL}, SMALL: {SMALL_MODEL}")
        logger.debug(f"Initializing agent with requested model: {model_name}")
            
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Code Generator LG"
            }
        )
        self.model_name = model_name
        logger.debug(f"BaseAgent initialized and ready with model: {model_name}")
        
    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main functionality"""
        pass
    
    def _invoke_model(self, messages: list) -> str:
        """Helper method to invoke the model with proper error handling"""
        try:
            # Log the request details
            logger.debug(f"Attempting to invoke model: {self.model_name}")
            logger.debug(f"Request messages: {[{'role': m.type, 'content': m.content[:100] + '...'} for m in messages]}")
            
            # Convert message roles: 'human' -> 'user'
            formatted_messages = []
            for m in messages:
                role = "user" if m.type == "human" else m.type
                formatted_messages.append({"role": role, "content": m.content})
            
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                max_tokens=8192,
                temperature=0.1
            )
            
            # Debug response
            logger.debug(f"Raw API response: {response}")
            
            # Add response validation
            if not response or not response.choices:
                logger.error(f"Invalid response structure: {response}")
                raise ValueError("Empty response received from API")
                
            message: ChatCompletionMessage = response.choices[0].message
            if not message or not message.content:
                logger.error(f"Invalid message structure: {message}")
                raise ValueError("No content in model response")
                
            logger.info(f"Successfully received response from {self.model_name}")
            logger.debug(f"Model response: {message.content[:100]}...")
            return message.content
            
        except Exception as e:
            logger.error(f"Error invoking model {self.model_name}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to get model response: {str(e)}")

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
