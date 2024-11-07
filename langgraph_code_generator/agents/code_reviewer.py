from typing import Dict, Any
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent, ANTHROPIC_SMALL_MODEL
import logging

logger = logging.getLogger(__name__)

class CodeReviewAgent(BaseAgent):
    def __init__(self):
        super().__init__(model_name=ANTHROPIC_SMALL_MODEL)
        
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Review the code using the code review agent"""
        logger.info("Starting code review step")
        
        prompt = """You are a code review agent. Review the Python code for:
1. Code quality and best practices
2. Potential bugs or issues
3. Security concerns
4. Performance considerations
5. Documentation completeness

Provide your response in XML format like this:
<review>
    <approved>true/false</approved>
    <issues>
        <issue>Issue description 1</issue>
        <issue>Issue description 2</issue>
    </issues>
    <suggestions>
        <suggestion>Suggestion 1</suggestion>
        <suggestion>Suggestion 2</suggestion>
    </suggestions>
</review>
"""

        review_message = f"""Review the following Python code:

{state['code']}

Execution result:
{state['execution_result']}
"""
        
        content = self._invoke_model([
            HumanMessage(content=prompt),
            HumanMessage(content=review_message)
        ])
        
        approved = (
            "true" in content.lower() and 
            "<approved>true</approved>" in content.lower()
        )
        
        logger.info(f"Code review complete. Approved: {approved}")
        return {
            "review_result": {"approved": approved, "raw_review": content},
            "next": "package" if approved else "generate",
        } 