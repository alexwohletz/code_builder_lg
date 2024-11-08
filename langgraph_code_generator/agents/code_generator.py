from typing import Dict, Any
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent
import logging
import xml.etree.ElementTree as ET
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class CodeGeneratorAgent(BaseAgent):
    def _is_valid_xml(self, xml_str: str) -> bool:
        """Validate if the string is complete, valid XML"""
        try:
            # Strip any leading/trailing whitespace
            xml_str = xml_str.strip()
            
            # Parse the XML
            root = ET.fromstring(xml_str)
            
            # Check for required elements, allowing for whitespace in element text
            if root.tag != "project":
                logger.warning(f"Root tag is '{root.tag}', expected 'project'")
                return False
                
            files_elem = root.find("files")
            if files_elem is None:
                logger.warning("Missing required 'files' element")
                return False
                
            requirements_elem = root.find("requirements")
            if requirements_elem is None:
                logger.warning("Missing required 'requirements' element")
                return False
                
            # Validate that at least one file exists
            if len(files_elem.findall("file")) == 0:
                logger.warning("No file elements found in 'files' section")
                return False
                
            return True
            
        except ET.ParseError as e:
            logger.warning(f"XML parsing error: {str(e)}")
            return False
        except Exception as e:
            logger.warning(f"Validation error: {str(e)}")
            return False
    prompt = """You are an expert Python developer. Analyze the requirements and generate an appropriate Python project structure.
First, determine if the requirements need multiple files or can be solved with a single file.

IMPORTANT: Your response must be a complete, valid XML document. Do not truncate or abbreviate the code.
Include the full implementation of all functions and classes.

Return an XML object with the following structure:

<project>
    <files>
        <!-- For single-file projects -->
        <file>
            <name>main.py</name>
            <content>
                # Complete implementation here
            </content>
        </file>
        <!-- OR for multi-file projects, include additional files as needed -->
        <file>
            <name>utils.py</name>
            <content>
                # Supporting code here
            </content>
        </file>
    </files>
    <requirements>
        <requirement>package1==version</requirement>
        <requirement>package2>=version</requirement>
    </requirements>
</project>

Guidelines:
DO NOT GENERATE UNIT TESTS, ONLY GENERATE CODE, A SEPERATE MODEL WILL HANDLE TESTS.

1. Analyze if the project needs multiple files:
   - Use single file for simple scripts, utilities, or small programs
   - Use multiple files for:
     * Projects with clear separation of concerns
     * Code that benefits from modularity
     * Projects with multiple distinct components
     * Large projects with different functionality groups

2. Code requirements:
   - Well-structured and modular when appropriate
   - Include proper error handling
   - Follow PEP 8 style guidelines
   - Include docstrings
   - Be efficient and maintainable
   - List all required pip packages with specific versions

DO NOT include any explanations, markdown formatting, or backticks.
Return ONLY the XML object, don't forget the closing tags.
"""
        
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code based on the prompt"""
        logger.info("Starting code generation step")
        
        attempts = state.get("attempts", 0)
        max_retries = 3  # Maximum number of retries for valid XML
        
        # Log the input prompt
        user_prompt = state["messages"][-1].content
        logger.info(f"Received prompt:\n{user_prompt}")
        
        for retry in range(max_retries):
            try:
                response = self._invoke_model([
                    HumanMessage(content=self.prompt),
                    state["messages"][-1]
                ])
                
                # Log the generated code
                logger.info(f"Generated code (attempt {retry + 1}):\n{response}")
                
                # Save to debug files
                debug_dir = "debug_output"
                os.makedirs(debug_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                with open(f"{debug_dir}/prompt_{timestamp}.txt", "w") as f:
                    f.write(user_prompt)
                
                with open(f"{debug_dir}/generated_code_{timestamp}_{retry+1}.xml", "w") as f:
                    f.write(response)
                
                if self._is_valid_xml(response):
                    logger.info("Code generation complete")
                    return {
                        "code": response,
                        "next": "execute",
                        "attempts": attempts + 1,
                    }
                
                logger.warning(f"Invalid XML generated (attempt {retry + 1}/{max_retries})")
                
            except Exception as e:
                logger.error(f"Error during code generation: {str(e)}")
        
        # If we get here, all retries failed
        logger.error("Failed to generate valid XML after all retries")
        return {
            "code": "<project><files/><requirements/></project>",  # Return minimal valid XML
            "next": "END",  # End the workflow
            "attempts": attempts + 1,
        }
