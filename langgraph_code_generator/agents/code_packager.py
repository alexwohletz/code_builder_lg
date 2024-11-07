from typing import Dict, Any
from .base_agent import BaseAgent
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class CodePackagerAgent(BaseAgent):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Package the approved code into a Python module"""
        logger.info("Starting code packaging step")
        
        try:
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
            
            # Write standalone file
            standalone_file = os.path.join(module_path, f"code_generated_{timestamp}.py")
            logger.info(f"Writing code to {standalone_file}")
            with open(standalone_file, "w") as f:
                f.write(state["code"])
                
            # Write __init__.py
            logger.info(f"Writing code to {module_path}/__init__.py")
            with open(os.path.join(module_path, "__init__.py"), "w") as f:
                f.write(state["code"])
                
            # Create setup.py
            setup_content = f"""
from setuptools import setup, find_packages

setup(
    name="{module_name}",
    version="0.1.0",
    packages=find_packages(),
    description="Generated Python module",
)
"""
            logger.info(f"Creating {module_path}/setup.py")
            with open(os.path.join(module_path, "setup.py"), "w") as f:
                f.write(setup_content)
                
            logger.info("Code packaging complete")
            return {
                "next": "END",
                "package_info": {
                    "standalone_file": os.path.relpath(standalone_file),
                    "module_path": os.path.relpath(module_path),
                },
            }
            
        except Exception as e:
            logger.error(f"Error during code packaging: {str(e)}")
            return {"next": "END"} 