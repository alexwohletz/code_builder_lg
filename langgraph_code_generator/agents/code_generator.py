from typing import Dict, Any
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)

class CodeGeneratorAgent(BaseAgent):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code based on the prompt"""
        logger.info("Starting code generation step")
        
        attempts = state.get("attempts", 0)
        
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
        
        last_message = state["messages"][-1]
        logger.info(f"Processing user prompt: {last_message.content[:100]}...")
        
        response = self._invoke_model([
            HumanMessage(content=prompt),
            last_message
        ])
        
        logger.info("Code generation complete")
        return {
            "code": response,  # Now contains XML with multiple files
            "next": "execute",
            "attempts": attempts + 1,
        }
