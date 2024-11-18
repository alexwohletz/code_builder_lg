import logging
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph_code_generator.agents.base_agent import BaseAgent
from langgraph_code_generator.agents.prompts.planner import PROMPT

logger = logging.getLogger(__name__)

class CodePlannerAgent(BaseAgent):
    """Agent responsible for analyzing requirements and creating a project plan."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create debug output directory if it doesn't exist
        self.debug_dir = Path("debug_output")
        self.debug_dir.mkdir(exist_ok=True)
        
    def _save_plan(self, plan: str, run_dir: Path) -> None:
        """Save the planning output to debug directory."""
        try:
            plan_file = run_dir / "plan.xml"
            with open(plan_file, 'w', encoding='utf-8') as f:
                f.write(plan)
            logger.info(f"Saved planning output to {plan_file}")
        except Exception as e:
            logger.error(f"Failed to save plan to debug directory: {e}")

    def _format_prompt(self, user_prompt: str) -> str:
        """Format the user prompt with the planning template."""
        return f"""
User Requirements:
{user_prompt}

Please analyze these requirements and provide a detailed project plan following this schema:
{PROMPT}
"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the planning phase of code generation."""
        logger.info("Starting planning phase")
        
        # Get the initial message from state
        messages = state.get("messages", [])
        if not messages:
            error_msg = "No messages found in state"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Extract user prompt from the first message
        user_prompt = messages[0].content
        logger.info(f"Processing user prompt: {user_prompt[:100]}...")
        
        # Create messages for the model
        formatted_prompt = self._format_prompt(user_prompt)
        messages = [
            SystemMessage(content="You are a code planning assistant that creates detailed XML project plans."),
            HumanMessage(content=formatted_prompt)
        ]
        
        try:
            # Generate the plan
            logger.info("Generating project plan")
            plan_xml = self._invoke_model(messages)
            
            # Create run directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = self.debug_dir / f"run_{timestamp}"
            run_dir.mkdir(exist_ok=True)
            
            # Save the plan in the run directory
            self._save_plan(plan_xml, run_dir)
            
            # Update state with the plan and run directory info
            logger.info("Updating state with generated plan")
            return {
                **state,
                "xml_state": plan_xml,
                "run_timestamp": timestamp,  # Pass timestamp to other agents
                "planning_result": {
                    "success": True,
                    "timestamp": timestamp,
                    "run_dir": str(run_dir),
                    "plan_file": "plan.xml"
                }
            }
            
        except Exception as e:
            logger.error(f"Error during planning phase: {str(e)}")
            return {
                **state,
                "planning_result": {
                    "success": False,
                    "error": str(e)
                }
            }
    
    def validate_xml(self, xml_content: str) -> bool:
        """Validate the XML against the base schema."""
        try:
            from lxml import etree
            
            # Load the base schema
            schema_path = Path(__file__).parent.parent / "BASE_SCHEMA.xml"
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_doc = etree.parse(f)
            
            # Create schema validator
            schema = etree.XMLSchema(schema_doc)
            
            # Parse and validate the XML content
            xml_doc = etree.fromstring(xml_content.encode())
            schema.assertValid(xml_doc)
            return True
            
        except Exception as e:
            logger.error(f"XML validation failed: {str(e)}")
            return False
