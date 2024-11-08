from typing import Dict, Any
import xml.etree.ElementTree as ET
from io import StringIO
from .base_agent import BaseAgent
from e2b_code_interpreter import Sandbox
import logging

logger = logging.getLogger(__name__)

class CodeExecutorAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sandbox = None
    
    @property
    def sandbox(self) -> Sandbox:
        """Lazy initialization of sandbox"""
        if self._sandbox is None:
            self._sandbox = Sandbox()
        return self._sandbox
        
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the generated code in the e2b sandbox"""
        logger.info("Starting code execution step")
        
        try:
            # Parse the XML response containing multiple files
            try:
                logger.info(f"Parsing XML content:\n{state['code']}")
                xml_root = ET.fromstring(state['code'])
                files = {}
                requirements = []
                
                # Extract files
                for file_elem in xml_root.findall('.//file'):
                    name = file_elem.find('name').text.strip()
                    content = file_elem.find('content').text.strip()
                    files[name] = content
                
                # Extract requirements
                for req_elem in xml_root.findall('.//requirement'):
                    requirements.append(req_elem.text.strip())
                    
            except ET.ParseError:
                raise ValueError("Invalid code format. Expected XML with project structure")

            # Write all files to the sandbox - directories will be created automatically
            for filename, content in files.items():
                filepath = f"/project/{filename}"
                logger.info(f"Writing file: {filepath}")
                # Convert string content to bytes for writing
                self.sandbox.files.write(filepath, content.encode())
            
            # Write requirements.txt if any requirements exist
            if requirements:
                requirements_content = "\n".join(requirements)
                self.sandbox.files.write("/project/requirements.txt", requirements_content.encode())
                
                # Install requirements
                logger.info("Installing requirements")
                install_result = self.sandbox.commands.run("cd /project && pip install -r requirements.txt")
                if install_result.error:
                    raise Exception(f"Failed to install requirements: {install_result.error}")
            
            # Execute main.py if it exists
            if "main.py" in files:
                logger.info("Executing main.py")
                logger.info(f"Code being executed:\n{files['main.py']}")
                execution = self.sandbox.commands.run("cd /project && python main.py")
            else:
                # If no main.py, execute the first Python file
                first_py_file = next((f for f in files.keys() if f.endswith('.py')), None)
                if not first_py_file:
                    raise ValueError("No Python files found in the generated code")
                logger.info(f"Executing {first_py_file}")
                logger.info(f"Code being executed:\n{files[first_py_file]}")
                execution = self.sandbox.commands.run(f"cd /project && python {first_py_file}")
            
            success = not bool(execution.error)
            logger.info(f"Code execution complete. Success: {success}")
            
            result = {
                "execution_result": {
                    "success": success,
                    "stdout": execution.stdout,
                    "stderr": execution.stderr,
                    "error": execution.error,
                }
            }
            
            if success:
                result["next"] = "review"
            else:
                result["next"] = "generate"
            
            return result
            
        except Exception as e:
            logger.error(f"Exception during code execution: {str(e)}")
            return {
                "execution_result": {"success": False, "error": str(e)},
                "next": "generate",
            }
    def _clean_test_code(self, test_code: str) -> str:
        """Clean up test cases before execution"""
        test_code = test_code.replace("```python", "").replace("```", "")
        return "\n".join(
            line for line in test_code.splitlines()
            if not (line.strip().startswith(("#", "Here", "Test", "This"))
                   and "print" not in line)
        )
        
    def cleanup(self):
        """Safe cleanup of sandbox resources"""
        if self._sandbox is not None:
            try:
                logger.info("Cleaning up sandbox")
                self._sandbox.kill()
            except Exception as e:
                logger.warning(f"Error during sandbox cleanup: {e}")
            finally:
                self._sandbox = None
        
    def __del__(self):
        """Ensure cleanup happens during garbage collection"""
        self.cleanup()
