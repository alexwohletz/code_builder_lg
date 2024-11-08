from typing import Dict, Any
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class CodeGeneratorAgent(BaseAgent):
    def _is_valid_xml(self, xml_str: str) -> bool:
        """Validate if the string is complete, valid XML"""
        try:
            root = ET.fromstring(xml_str)
            # Check for required elements
            if root.tag != "project":
                return False
            if not root.find("files"):
                return False
            if not root.find("requirements"):
                return False
            return True
        except Exception:
            return False
    prompt = """You are an expert Python developer. Analyze the requirements and generate an appropriate Python project structure.
First, determine if the requirements need multiple files or can be solved with a single file.

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
Return ONLY the XML object.
"""
        
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code based on the prompt"""
        logger.info("Starting code generation step")
        
        attempts = state.get("attempts", 0)
        max_retries = 3  # Maximum number of retries for valid XML
        
        for retry in range(max_retries):
            try:
                response = self._invoke_model([
                    HumanMessage(content=self.prompt),
                    state["messages"][-1]
                ])
                
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
