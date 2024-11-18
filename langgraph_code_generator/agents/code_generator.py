import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
import xml.etree.ElementTree as ET

from langgraph_code_generator.agents.base_agent import BaseAgent
from langgraph_code_generator.agents.prompts.generator import PROMPT

logger = logging.getLogger(__name__)

class CodeGeneratorAgent(BaseAgent):
    """Agent responsible for generating code based on the planning XML."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.debug_dir = Path("debug_output")
        self.debug_dir.mkdir(exist_ok=True)
    
    def _save_generated_code(self, xml_content: str, timestamp: str) -> None:
        """Save the generated code XML to debug directory."""
        try:
            output_file = self.debug_dir / f"generated_code_{timestamp}.xml"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            logger.info(f"Saved generated code to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save generated code: {e}")
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the code generation phase."""
        logger.info("Starting code generation phase")
        
        # Get the XML state from the planner
        xml_state = state.get("xml_state")
        if not xml_state:
            error_msg = "No XML state found in state"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Log the XML state for debugging
            logger.debug(f"Received XML state: {xml_state[:200]}...")
            
            # Create messages for the model using the PROMPT from generator.py
            messages = [
                SystemMessage(content="You are an expert Python code generator."),
                HumanMessage(content=PROMPT.format(xml_state=xml_state))
            ]
            
            # Generate the code
            logger.info("Generating code based on plan")
            generated_xml = self._invoke_model(messages)
            
            # Add detailed XML logging
            logger.debug("Generated XML Structure:")
            logger.debug("-" * 80)
            logger.debug(generated_xml)
            logger.debug("-" * 80)
            
            # Attempt to clean the response if it contains any conversation
            if not generated_xml.strip().startswith('<code_project'):
                logger.warning("Response doesn't start with XML - attempting to extract")
                # Try to find XML content
                xml_start = generated_xml.find('<code_project')
                xml_end = generated_xml.rfind('</code_project>') + len('</code_project>')
                if xml_start >= 0 and xml_end > xml_start:
                    generated_xml = generated_xml[xml_start:xml_end]
                    logger.debug("Extracted XML:")
                    logger.debug(generated_xml)
                else:
                    raise ValueError("Could not find valid XML in response")
            
            # Save the generated code with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._save_generated_code(generated_xml, timestamp)
            
            # Validate the generated XML
            if not self.validate_xml(generated_xml):
                logger.error("Generated XML failed validation")
                return {
                    **state,
                    "generation_result": {
                        "success": False,
                        "error": "XML validation failed"
                    }
                }
            
            # Log the state being passed to executor
            logger.debug("Passing XML state to executor:")
            logger.debug("-" * 80)
            logger.debug(generated_xml[:200] + "..." if len(generated_xml) > 200 else generated_xml)
            logger.debug("-" * 80)
            
            # Update state with generated code
            logger.info("Updating state with generated code")
            return {
                **state,
                "xml_state": generated_xml,
                "generation_result": {
                    "success": True,
                    "timestamp": timestamp,
                    "generated_file": f"generated_code_{timestamp}.xml"
                }
            }
            
        except Exception as e:
            logger.error(f"Error during code generation: {str(e)}", exc_info=True)
            return {
                **state,
                "generation_result": {
                    "success": False,
                    "error": str(e)
                }
            }
    
    def validate_xml(self, xml_content: str) -> bool:
        """Validate the XML against the base schema."""
        try:
            from lxml import etree
            
            # Load the base schema
            schema_path = Path(__file__).parent.parent / "BASE_SCHEMA.xml"
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_doc = etree.parse(f)
            
            # Create schema validator
            schema = etree.XMLSchema(schema_doc)
            
            # Parse and validate the XML content
            xml_doc = etree.fromstring(xml_content.encode())
            schema.assertValid(xml_doc)
            return True
            
        except Exception as e:
            logger.error(f"XML validation failed: {str(e)}")
            return False
