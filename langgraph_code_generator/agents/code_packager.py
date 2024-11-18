from typing import Dict, Any
from .base_agent import BaseAgent
from datetime import datetime
import os
import logging
import shutil
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class CodePackagerAgent(BaseAgent):
    """Agent responsible for packaging generated code into a deployable module.
    
    This agent:
    1. Extracts files from the XML generation section
    2. Creates a clean package structure with src/ and tests/ directories
    3. Handles dependencies and creates requirements.txt
    4. Generates setup.py and other necessary package files
    5. Updates the XML with package information
    """
    
    def _safe_get_text(self, element: ET.Element, default: str = "") -> str:
        """Safely get text from an XML element with a default value if None"""
        if element is not None and element.text is not None:
            return element.text.strip()
        return default
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Package the approved code into a deployable module"""
        logger.info("Starting code packaging step")
        
        try:
            # Parse the XML state
            xml_root = self.parse_xml(state['xml_state'])
            
            # Create timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create base directory for generated modules
            base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_modules")
            logger.info(f"Creating {base_dir} directory")
            os.makedirs(base_dir, exist_ok=True)
            
            # Get project name from metadata or use default
            project_name = xml_root.find('./metadata/project_name')
            module_name = f"{self._safe_get_text(project_name, 'generated_module')}_{timestamp}"
            module_path = os.path.join(base_dir, module_name)
            
            # Create fresh module directory
            if os.path.exists(module_path):
                shutil.rmtree(module_path)
            os.makedirs(module_path)
            logger.info(f"Created module directory: {module_path}")
            
            # Create src directory for code files
            src_path = os.path.join(module_path, "src")
            os.makedirs(src_path)
            
            # Extract and write all files from generation section
            files_written = []
            for file_elem in xml_root.findall('./generation/files/file'):
                file_name_elem = file_elem.find('file_name')
                file_path_elem = file_elem.find('file_path')
                file_contents_elem = file_elem.find('file_contents')
                
                if file_name_elem is None or file_contents_elem is None:
                    logger.warning(f"Skipping file with missing name or contents: {ET.tostring(file_elem)}")
                    continue
                
                file_name = self._safe_get_text(file_name_elem)
                file_contents = self._safe_get_text(file_contents_elem)
                
                if not file_name:
                    logger.warning("Skipping file with empty name")
                    continue
                
                # Determine the target path
                if file_path_elem is not None:
                    relative_path = self._safe_get_text(file_path_elem)
                    target_path = os.path.join(module_path, relative_path) if relative_path else os.path.join(src_path, file_name)
                else:
                    target_path = os.path.join(src_path, file_name)
                
                # Create directories if needed
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                logger.info(f"Writing file: {target_path}")
                with open(target_path, "w") as f:
                    f.write(file_contents)
                files_written.append(os.path.relpath(target_path, module_path))
            
            # Extract dependencies from the dependencies section
            dependencies = []
            for dep_elem in xml_root.findall('./dependencies/dependency'):
                name_elem = dep_elem.find('name')
                version_elem = dep_elem.find('version')
                
                if name_elem is None:
                    continue
                    
                name = self._safe_get_text(name_elem)
                if not name:
                    continue
                    
                if version_elem is not None:
                    version = self._safe_get_text(version_elem)
                    if version:
                        dependencies.append(f"{name}=={version}")
                    else:
                        dependencies.append(name)
                else:
                    dependencies.append(name)
            
            # Write requirements.txt if there are dependencies
            if dependencies:
                requirements_path = os.path.join(module_path, "requirements.txt")
                logger.info(f"Writing requirements to {requirements_path}")
                with open(requirements_path, "w") as f:
                    f.write("\n".join(dependencies))
                files_written.append("requirements.txt")
            
            # Create __init__.py files for Python package structure
            for dir_path in [module_path, src_path]:
                init_path = os.path.join(dir_path, "__init__.py")
                with open(init_path, "w") as f:
                    f.write(f"# {module_name}\n")
                rel_path = os.path.relpath(init_path, module_path)
                files_written.append(rel_path)
            
            # Create setup.py with project metadata
            description = xml_root.find('./metadata/description')
            description_text = self._safe_get_text(description, "Generated Python module")
            
            setup_content = f"""
from setuptools import setup, find_packages

setup(
    name="{module_name}",
    version="0.1.0",
    packages=find_packages(),
    description="{description_text}",
    install_requires={repr(dependencies) if dependencies else '[]'},
    python_requires='>=3.8',
)
"""
            setup_path = os.path.join(module_path, "setup.py")
            logger.info(f"Creating {setup_path}")
            with open(setup_path, "w") as f:
                f.write(setup_content)
            files_written.append("setup.py")
            
            # Copy test files from the test suite if they exist
            test_files = xml_root.findall('./generation/test_suite/test_files/test_file')
            if test_files:
                tests_path = os.path.join(module_path, "tests")
                os.makedirs(tests_path, exist_ok=True)
                
                # Create test __init__.py
                with open(os.path.join(tests_path, "__init__.py"), "w") as f:
                    f.write("# Test suite\n")
                files_written.append("tests/__init__.py")
                
                for test_file in test_files:
                    test_name_elem = test_file.find('test_file_name')
                    test_code_elem = test_file.find('./tests/test/test_code')
                    
                    if test_name_elem is None or test_code_elem is None:
                        logger.warning("Skipping test file with missing name or code")
                        continue
                        
                    test_name = self._safe_get_text(test_name_elem)
                    test_code = self._safe_get_text(test_code_elem)
                    
                    if not test_name or not test_code:
                        logger.warning("Skipping test file with empty name or code")
                        continue
                    
                    test_path = os.path.join(tests_path, test_name)
                    with open(test_path, "w") as f:
                        f.write(test_code)
                    files_written.append(f"tests/{test_name}")
            
            # Update the package section in the XML with build results
            package_elem = xml_root.find('./package')
            if package_elem is None:
                package_elem = ET.SubElement(xml_root, 'package')
            
            # Clear existing package info for clean update
            package_elem.clear()
            
            # Add package metadata
            ET.SubElement(package_elem, 'package_name').text = module_name
            ET.SubElement(package_elem, 'package_version').text = "0.1.0"
            
            # Add list of packaged files
            files_elem = ET.SubElement(package_elem, 'package_files')
            for file_path in files_written:
                file_elem = ET.SubElement(files_elem, 'package_file')
                file_elem.text = file_path
            
            # Add package metadata
            metadata_elem = ET.SubElement(package_elem, 'package_metadata')
            ET.SubElement(metadata_elem, 'license').text = "MIT"
            
            # Update the XML state in the workflow state
            state['xml_state'] = self.generate_xml(xml_root)
            
            logger.info("Code packaging complete")
            return {
                "package_result": {
                    "success": True,
                    "module_path": os.path.relpath(module_path),
                    "files": files_written,
                    "dependencies": dependencies,
                }
            }
            
        except Exception as e:
            logger.error(f"Error during code packaging: {str(e)}")
            return {
                "package_result": {
                    "success": False,
                    "error": str(e)
                }
            }
