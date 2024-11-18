import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
from langchain_core.messages import SystemMessage, HumanMessage

from langgraph_code_generator.agents.base_agent import BaseAgent
from langgraph_code_generator.agents.prompts.generator import PROMPT

logger = logging.getLogger(__name__)

class CodeGeneratorAgent(BaseAgent):
    """Agent responsible for generating code based on the planning XML."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.debug_dir = Path("debug_output")
        self.debug_dir.mkdir(exist_ok=True)
    
    def _save_generated_code(self, xml_content: str, run_dir: Path) -> None:
        """Save the generated code XML to debug directory."""
        try:
            output_file = run_dir / "generated_code.xml"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            logger.info(f"Saved generated code to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save generated code: {e}")
    
    def _clean_xml_response(self, response: str) -> str:
        """Clean and extract valid XML from the response."""
        try:
            # Find the start and end of the XML content
            xml_start = response.find('<code_project')
            xml_end = response.rfind('</code_project>') + len('</code_project>')
            
            if xml_start < 0 or xml_end <= xml_start:
                raise ValueError("Could not find valid XML structure")
            
            xml_content = response[xml_start:xml_end]
            
            # Validate basic XML structure
            ET.fromstring(xml_content)
            
            return xml_content
            
        except Exception as e:
            logger.error(f"Failed to clean XML response: {e}")
            raise
    
    def _verify_required_sections(self, xml_content: str) -> bool:
        """Verify that all required sections are present in the correct order."""
        try:
            root = ET.fromstring(xml_content)
            required_sections = ['metadata', 'planning', 'generation', 'dependencies', 'build', 'package']
            
            # Get all child elements
            children = [child.tag for child in root]
            
            # Check if all required sections are present
            for section in required_sections:
                if section not in children:
                    logger.error(f"Missing required section: {section}")
                    return False
            
            # Check if sections are in correct order
            current_index = -1
            for section in required_sections:
                index = children.index(section)
                if index <= current_index:
                    logger.error(f"Section {section} is out of order")
                    return False
                current_index = index
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify XML sections: {e}")
            return False
    
    def validate_xml(self, xml_content: str) -> bool:
        """Validate the XML against the XSD schema."""
        try:
            from lxml import etree
            
            # First verify required sections and order
            if not self._verify_required_sections(xml_content):
                return False
            
            # Load the XSD schema
            schema_path = Path(__file__).parent.parent / "BASE_SCHEMA.xsd"
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_doc = etree.parse(f)
            
            # Create schema validator
            schema = etree.XMLSchema(schema_doc)
            
            # Parse and validate the XML content
            xml_doc = etree.fromstring(xml_content.encode())
            
            try:
                schema.assertValid(xml_doc)
                logger.info("XML validation successful")
                return True
            except etree.DocumentInvalid as e:
                logger.error(f"XML validation failed: {str(e)}")
                # Log detailed validation errors
                for error in schema.error_log:
                    logger.error(f"Line {error.line}: {error.message}")
                return False
            
        except Exception as e:
            logger.error(f"XML validation error: {str(e)}")
            return False
    
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
            response = self._invoke_model(messages)
            
            # Clean and validate the response
            logger.debug("Cleaning and validating generated XML")
            try:
                generated_xml = self._clean_xml_response(response)
            except Exception as e:
                logger.error(f"Failed to clean XML response: {e}")
                return {
                    **state,
                    "generation_result": {
                        "success": False,
                        "error": f"XML cleaning failed: {str(e)}"
                    }
                }
            
            # Get run directory from state
            timestamp = state.get("run_timestamp")
            if not timestamp:
                logger.warning("No run timestamp found in state, generating new one")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            run_dir = self.debug_dir / f"run_{timestamp}"
            run_dir.mkdir(exist_ok=True)
            
            # Save the generated code in the run directory
            self._save_generated_code(generated_xml, run_dir)
            
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
            
            # Update state with generated code
            logger.info("Updating state with generated code")
            return {
                **state,
                "xml_state": generated_xml,
                "generation_result": {
                    "success": True,
                    "run_dir": str(run_dir),
                    "generated_file": "generated_code.xml"
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
