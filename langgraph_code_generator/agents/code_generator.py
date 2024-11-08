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
        
        prompt = """You are an expert Python developer. Generate a complete Python project.
Return an XML object with the following structure:

<project>
    <files>
        <file>
            <name>main.py</name>
            <content>
                def main():
                    # Your code here
            </content>
        </file>
        <file>
            <name>utils.py</name>
            <content>
                def helper():
                    # Your code here
            </content>
        </file>
    </files>
    <requirements>
        <requirement>package1</requirement>
        <requirement>package2</requirement>
    </requirements>
</project>

Requirements for the code:
1. Well-structured and modular
2. Include proper error handling
3. Follow PEP 8 style guidelines
4. Include docstrings
5. Be efficient and maintainable
6. List all required pip packages with versions

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
