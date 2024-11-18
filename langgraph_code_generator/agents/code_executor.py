import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
from e2b_code_interpreter import Sandbox

from langgraph_code_generator.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class CodeExecutorAgent(BaseAgent):
    """Agent responsible for executing generated code in a sandbox environment."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sandbox = None
        self.debug_dir = Path("debug_output")
        self.debug_dir.mkdir(exist_ok=True)
    
    @property
    def sandbox(self) -> Sandbox:
        """Lazy initialization of sandbox."""
        if self._sandbox is None:
            self._sandbox = Sandbox()
        return self._sandbox

    def _save_execution_files(self, files: Dict[str, str], timestamp: str) -> None:
        """Save files being executed for debugging."""
        try:
            for filename, content in files.items():
                debug_file = self.debug_dir / f"execution_{timestamp}_{filename}"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Saved execution file to {debug_file}")
        except Exception as e:
            logger.error(f"Failed to save execution files: {e}")

    def _extract_files_from_xml(self, xml_state: str) -> Dict[str, str]:
        """Extract files and their contents from XML state."""
        try:
            # Add detailed XML logging
            logger.debug("Executor received XML state:")
            logger.debug("-" * 80)
            logger.debug(xml_state[:200] + "..." if len(xml_state) > 200 else xml_state)
            logger.debug("-" * 80)
            
            root = ET.fromstring(xml_state)
            logger.debug(f"Parsed XML root tag: {root.tag}")
            
            files = {}
            
            # Extract all files from the generation section
            generation = root.find('.//generation')
            if generation is None:
                logger.error("No generation section found in XML")
                # Log the full XML structure for debugging
                logger.debug("Full XML structure:")
                for elem in root.iter():
                    logger.debug(f"Element: {elem.tag}")
                return {}
            
            # Log generation section contents
            logger.debug("Found generation section:")
            for elem in generation.iter():
                logger.debug(f"  {elem.tag}")
            
            for file_elem in generation.findall('.//file'):
                file_name = file_elem.find('file_name')
                file_contents = file_elem.find('file_contents')
                
                if file_name is not None and file_contents is not None:
                    name = file_name.text.strip()
                    contents = file_contents.text.strip()
                    logger.debug(f"Found file in XML: {name}")
                    files[name] = contents
                else:
                    logger.warning(f"Incomplete file entry found in XML")
            
            # Extract test files
            test_suite = root.find('.//test_suite')
            if test_suite is not None:
                for test_file in test_suite.findall('.//test_file'):
                    test_name = test_file.find('test_file_name')
                    test_code_elem = test_file.find('.//test_code')
                    
                    if test_name is not None and test_code_elem is not None:
                        name = test_name.text.strip()
                        code = test_code_elem.text.strip()
                        logger.debug(f"Found test file in XML: {name}")
                        files[name] = code
            
            if not files:
                logger.warning("No files were extracted from the XML")
            else:
                logger.info(f"Successfully extracted {len(files)} files from XML")
            
            return files
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to extract files from XML: {e}")
            raise

    def _update_test_results_in_xml(self, xml_state: str, result: Dict[str, Any]) -> str:
        """Update the test results in the XML state."""
        try:
            root = ET.fromstring(xml_state)
            
            # Find all test files in the XML
            for test_file in root.findall('.//test_suite/test_files/test_file'):
                # Create or get the test_results element
                test_results = test_file.find('test_results')
                if test_results is None:
                    test_results = ET.SubElement(test_file, 'test_results')
                
                # Clear any existing results
                test_results.clear()
                
                # Add new result
                result_elem = ET.SubElement(test_results, 'result')
                
                # Add status
                status = ET.SubElement(result_elem, 'status')
                status.text = 'passed' if result.get('success', False) else 'failed'
                
                # Add output
                output = ET.SubElement(result_elem, 'output')
                output.text = result.get('stdout', '')
                
                # Add error if present
                if result.get('error'):
                    error = ET.SubElement(result_elem, 'error')
                    error.text = str(result['error'])
                
                # Add timestamp
                timestamp = ET.SubElement(result_elem, 'timestamp')
                timestamp.text = result.get('timestamp', '')
            
            # Convert back to string
            return ET.tostring(root, encoding='unicode', method='xml')
            
        except Exception as e:
            logger.error(f"Failed to update test results in XML: {e}")
            return xml_state  # Return original XML if update fails

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the generated code in the sandbox environment."""
        logger.info("Starting code execution phase")
        
        # Check if generation was successful
        generation_result = state.get("generation_result", {})
        if not generation_result.get("success", False):
            logger.error("Cannot execute code - generation was not successful")
            return {
                **state,
                "sandbox_result": {
                    "success": False,
                    "error": "Code generation failed, skipping execution",
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
                }
            }
        
        xml_state = state.get("xml_state")
        if not xml_state:
            error_msg = "No XML state found in state"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Extract files from XML
            files = self._extract_files_from_xml(xml_state)
            if not files:
                raise ValueError("No files found in XML state")
            
            # Save files for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._save_execution_files(files, timestamp)
            
            # Write files to sandbox
            for filename, content in files.items():
                logger.info(f"Writing file to sandbox: {filename}")
                self.sandbox.files.write(f"/code/{filename}", content.encode())
            
            # Run tests if they exist
            test_files = [f for f in files.keys() if f.startswith('test_')]
            if test_files:
                logger.info("Running tests")
                result = self.sandbox.commands.run(
                    "cd /code && python -m pytest -v",
                    background=True
                )
            else:
                # If no tests, run main.py
                logger.info("No tests found, running main.py")
                result = self.sandbox.commands.run(
                    "cd /code && python main.py",
                    background=True
                )
            
            success = not bool(result.error)
            logger.info(f"Execution completed. Success: {success}")
            
            # Create execution result
            execution_result = {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.error if result.error else None,
                "timestamp": timestamp
            }
            
            # Update test results in XML
            updated_xml = self._update_test_results_in_xml(xml_state, execution_result)
            
            return {
                **state,
                "xml_state": updated_xml,  # Return updated XML
                "sandbox_result": execution_result
            }
            
        except Exception as e:
            logger.error(f"Error during execution: {str(e)}")
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            
            # Update XML with error result
            updated_xml = self._update_test_results_in_xml(xml_state, error_result)
            
            return {
                **state,
                "xml_state": updated_xml,
                "sandbox_result": error_result
            }

    def cleanup(self):
        """Cleanup sandbox resources."""
        if self._sandbox is not None:
            try:
                logger.info("Cleaning up sandbox")
                self._sandbox.kill()
            except Exception as e:
                logger.warning(f"Error during sandbox cleanup: {e}")
            finally:
                self._sandbox = None
    
    def __del__(self):
        """Ensure cleanup during garbage collection."""
        self.cleanup()
