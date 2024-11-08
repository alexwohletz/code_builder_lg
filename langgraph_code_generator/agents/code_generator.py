from typing import Dict, Any
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent
import logging
import xml.etree.ElementTree as ET
import os
from datetime import datetime
import io, re
from xml.dom import minidom
from .utils import escape_python_code
logger = logging.getLogger(__name__)

class CodeGeneratorAgent(BaseAgent):
    def _escape_code_content(self, xml_str: str) -> str:
        """
        Escape special characters in code content sections.
        
        Args:
            xml_str: Raw XML string
            
        Returns:
            XML string with escaped content sections
        """
        def escape_content(match):
            """Escape special characters in content section"""
            content = match.group(2)
            return f"{match.group(1)}{escape_python_code(content)}{match.group(3)}"
        
        # Find and escape content between <content> tags
        return re.sub(
            r'(<content>)(.*?)(</content>)',
            escape_content,
            xml_str,
            flags=re.DOTALL
        )

    def _is_valid_xml(self, xml_str: str) -> bool:
        """
        Validate if the string is complete, valid XML according to project requirements.
        
        Args:
            xml_str: String containing XML content to validate
            
        Returns:
            bool: True if XML is valid according to project structure requirements
        """
        try:
            # Always escape the content sections first
            xml_str = self._escape_code_content(xml_str)
            
            # Parse with minidom
            doc = minidom.parseString(xml_str)
            root = doc.documentElement

            # Check for basic structure
            if root.tagName != "project":
                logger.debug("Root element is not 'project'")
                return False

            # Check for required elements
            files = doc.getElementsByTagName("files")
            if not files:
                logger.debug("Missing 'files' element")
                return False

            requirements = doc.getElementsByTagName("requirements")
            if not requirements:
                logger.debug("Missing 'requirements' element")
                return False

            # Check files section
            file_elements = doc.getElementsByTagName("file")
            if not file_elements:
                logger.debug("No file elements found")
                return False

            # Validate each file has required elements
            for file_elem in file_elements:
                name_elements = file_elem.getElementsByTagName("name")
                content_elements = file_elem.getElementsByTagName("content")
                
                if not name_elements or not name_elements[0].firstChild:
                    logger.debug("File missing name")
                    return False
                
                if not content_elements:
                    logger.debug("File missing content")
                    return False

            logger.debug("XML validation successful")
            return True

        except Exception as e:
            logger.debug(f"XML validation error: {str(e)}")
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
                
                # Escape the code content before saving and validating
                escaped_response = self._escape_code_content(response)
                
                with open(f"{debug_dir}/generated_code_{timestamp}_{retry+1}.xml", "w") as f:
                    f.write(escaped_response)
                
                if self._is_valid_xml(escaped_response):
                    logger.info("Code generation complete")
                    return {
                        "code": escaped_response,  # Return the escaped version
                        "next": "execute",
                        "attempts": attempts + 1,
                    }
                
                logger.warning(f"Invalid XML generated (attempt {retry + 1}/{max_retries})")
                
            except Exception as e:
                logger.error(f"Error during code generation: {str(e)}")
        
        # If we get here, all retries failed
        logger.error("Failed to generate valid XML after all retries")
        return {
            "code": "<project><files/><requirements/></project>",
            "next": "END",
            "attempts": attempts + 1,
        }
