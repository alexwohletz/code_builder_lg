import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
import xml.etree.ElementTree as ET

from langgraph_code_generator.agents.base_agent import BaseAgent
from langgraph_code_generator.agents.prompts.iterator import PROMPT

logger = logging.getLogger(__name__)

class CodeIteratorAgent(BaseAgent):
    """Agent responsible for analyzing test failures and updating the planning XML."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.debug_dir = Path("debug_output")
        self.debug_dir.mkdir(exist_ok=True)
    
    def _save_iteration_analysis(self, xml_content: str, timestamp: str) -> None:
        """Save the iteration analysis to debug directory."""
        try:
            output_file = self.debug_dir / f"iteration_{timestamp}.xml"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            logger.info(f"Saved iteration analysis to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save iteration analysis: {e}")

    def _extract_test_results(self, xml_state: str) -> Dict[str, Any]:
        """Extract test results from XML state."""
        try:
            root = ET.fromstring(xml_state)
            results = {}
            
            # Collect all test results
            for test_file in root.findall('.//test_suite/test_files/test_file'):
                test_name = test_file.find('test_file_name').text.strip()
                test_results = test_file.find('test_results/result')
                
                if test_results is not None:
                    results[test_name] = {
                        'status': test_results.find('status').text,
                        'output': test_results.find('output').text if test_results.find('output') is not None else '',
                        'error': test_results.find('error').text if test_results.find('error') is not None else None
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to extract test results: {e}")
            raise

    def _merge_planning_updates(self, original_xml: str, updated_planning: str) -> str:
        """Merge updated planning section into the original XML while preserving structure and order."""
        try:
            original_root = ET.fromstring(original_xml)
            updated_root = ET.fromstring(updated_planning)
            
            # Define the expected order of sections
            section_order = ["metadata", "planning", "generation", "dependencies", "build", "package"]
            
            # Find and extract the updated planning section
            updated_planning_section = updated_root.find('.//planning')
            if updated_planning_section is None:
                logger.error("No planning section found in updated XML")
                return original_xml
            
            # Create a new root element
            new_root = ET.Element('code_project')
            
            # Copy sections in the correct order, replacing planning with the updated version
            for section_name in section_order:
                if section_name == "planning":
                    # Use the updated planning section
                    new_root.append(updated_planning_section)
                else:
                    # Copy the original section
                    original_section = original_root.find(section_name)
                    if original_section is not None:
                        new_root.append(original_section)
                    else:
                        # Create empty section if it doesn't exist
                        new_section = ET.SubElement(new_root, section_name)
            
            # Convert to string while preserving formatting
            return ET.tostring(new_root, encoding='unicode', method='xml')
            
        except Exception as e:
            logger.error(f"Failed to merge planning updates: {e}")
            return original_xml

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the iteration analysis phase."""
        logger.info("Starting iteration analysis phase")
        
        xml_state = state.get("xml_state")
        if not xml_state:
            error_msg = "No XML state found in state"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Extract test results
            test_results = self._extract_test_results(xml_state)
            if not test_results:
                logger.warning("No test results found in XML state")
            
            # Create messages for the model
            messages = [
                SystemMessage(content="You are an expert code quality analyst."),
                HumanMessage(content=PROMPT.format(
                    xml_state=xml_state,
                    timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
                ))
            ]
            
            # Generate iteration analysis
            logger.info("Analyzing test results and generating updates")
            updated_planning = self._invoke_model(messages)
            
            # Save the iteration analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._save_iteration_analysis(updated_planning, timestamp)
            
            # Merge updated planning into original XML
            updated_xml = self._merge_planning_updates(xml_state, updated_planning)
            
            # Validate the updated XML
            if not self.validate_xml(updated_xml):
                raise ValueError("Updated XML failed validation")
            
            # Verify all required sections are present
            root = ET.fromstring(updated_xml)
            required_sections = ["metadata", "planning", "generation", "dependencies", "build", "package"]
            missing_sections = [section for section in required_sections if root.find(section) is None]
            if missing_sections:
                raise ValueError(f"Missing required sections after update: {', '.join(missing_sections)}")
            
            logger.info("Successfully updated planning based on test results")
            return {
                **state,
                "xml_state": updated_xml,
                "iteration_result": {
                    "success": True,
                    "timestamp": timestamp,
                    "iteration_file": f"iteration_{timestamp}.xml"
                }
            }
            
        except Exception as e:
            logger.error(f"Error during iteration analysis: {str(e)}")
            return {
                **state,
                "iteration_result": {
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
