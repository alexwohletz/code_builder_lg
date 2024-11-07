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
        
        prompt = """You are a Python code generation agent. Generate ONLY the Python function code.
DO NOT include any explanations, markdown formatting, or backticks.
DO NOT include any text before or after the code.
Start directly with 'def' and end with the last line of code.

Requirements:
1. Well-structured and modular
2. Include proper error handling
3. Follow PEP 8 style guidelines
4. Include docstrings
5. Be efficient and maintainable
"""
        
        last_message = state["messages"][-1]
        logger.info(f"Processing user prompt: {last_message.content[:100]}...")
        
        response = self._invoke_model([
            HumanMessage(content=prompt),
            last_message
        ])
        
        logger.info("Code generation complete")
        return {
            "code": response,
            "next": "execute",
            "attempts": attempts + 1,
        } 