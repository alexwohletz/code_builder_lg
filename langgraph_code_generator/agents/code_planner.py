from langgraph_code_generator.agents.base_agent import BaseAgent
from langchain_core.messages import HumanMessage
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class CodePlannerAgent(BaseAgent):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = self.get_from_state(state, 'user_prompt')
        if not user_prompt:
            logger.error("No user prompt found in state.")
            raise ValueError("Missing 'user_prompt' in state.")

        logger.info("Planning code based on user prompt.")
        messages = [
            HumanMessage(content=f"Plan out the code elements needed to meet the following requirements:\n{user_prompt}")
        ]
        plan = self._invoke_model(messages)
        logger.debug(f"Code plan: {plan}")

        # Assuming the plan is in JSON format for structured requirements
        try:
            import json
            plan_dict = json.loads(plan)
            self.update_state(state, 'code_requirements', plan_dict)
        except json.JSONDecodeError:
            logger.error("Failed to parse plan into JSON.")
            raise

        return state