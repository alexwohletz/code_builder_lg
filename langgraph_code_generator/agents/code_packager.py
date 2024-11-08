from typing import Dict, Any
from .base_agent import BaseAgent
from datetime import datetime
import os
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class CodePackagerAgent(BaseAgent):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Package the approved code into a Python module"""
        logger.info("Starting code packaging step")
        
        try:
            # Parse the XML project structure
            xml_root = ET.fromstring(state['code'])
            
            # Create timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create base directory for generated modules
            base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_modules")
            logger.info(f"Creating {base_dir} directory")
            os.makedirs(base_dir, exist_ok=True)
            
            # Create timestamped module directory
            module_name = f"generated_module_{timestamp}"
            module_path = os.path.join(base_dir, module_name)
            os.makedirs(module_path, exist_ok=True)
            
            # Extract and write all files
            files_written = []
            for file_elem in xml_root.findall('.//file'):
                filename = file_elem.find('name').text.strip()
                content = file_elem.find('content').text.strip()
                
                file_path = os.path.join(module_path, filename)
                logger.info(f"Writing file: {file_path}")
                with open(file_path, "w") as f:
                    f.write(content)
                files_written.append(os.path.relpath(file_path))
            
            # Extract and write requirements
            requirements = []
            for req_elem in xml_root.findall('.//requirement'):
                requirement = req_elem.text.strip()
                requirements.append(requirement)
            
            if requirements:
                requirements_path = os.path.join(module_path, "requirements.txt")
                logger.info(f"Writing requirements to {requirements_path}")
                with open(requirements_path, "w") as f:
                    f.write("\n".join(requirements))
                files_written.append(os.path.relpath(requirements_path))
                
            # Create __init__.py if it doesn't exist
            init_path = os.path.join(module_path, "__init__.py")
            if not os.path.exists(init_path):
                logger.info(f"Creating {init_path}")
                with open(init_path, "w") as f:
                    f.write("# Generated module\n")
                files_written.append(os.path.relpath(init_path))
                
            # Create setup.py with dependencies
            setup_content = f"""
from setuptools import setup, find_packages

setup(
    name="{module_name}",
    version="0.1.0",
    packages=find_packages(),
    description="Generated Python module",
    install_requires={repr(requirements) if requirements else '[]'},
)
"""
            setup_path = os.path.join(module_path, "setup.py")
            logger.info(f"Creating {setup_path}")
            with open(setup_path, "w") as f:
                f.write(setup_content)
            files_written.append(os.path.relpath(setup_path))
                
            logger.info("Code packaging complete")
            return {
                "next": "END",
                "package_info": {
                    "module_path": os.path.relpath(module_path),
                    "files": files_written,
                    "requirements": requirements,
                },
            }
            
        except Exception as e:
            logger.error(f"Error during code packaging: {str(e)}")
            return {"next": "END"}
