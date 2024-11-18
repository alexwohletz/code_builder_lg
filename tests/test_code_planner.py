import unittest
from pathlib import Path
from langgraph_code_generator.agents.code_planner import CodePlannerAgent
from langchain_core.messages import HumanMessage

class TestCodePlannerAgent(unittest.TestCase):
    def setUp(self):
        self.planner = CodePlannerAgent()
        self.test_state = {
            "messages": [
                HumanMessage(content="Create a simple web server that handles GET and POST requests")
            ]
        }

    def test_planning_phase(self):
        result = self.planner.run(self.test_state)
        
        # Check if planning was successful
        self.assertTrue(result["planning_result"]["success"])
        
        # Verify XML state was updated
        self.assertIsNotNone(result["xml_state"])
        
        # Check if debug file was created
        plan_file = Path("debug_output") / result["planning_result"]["plan_file"]
        self.assertTrue(plan_file.exists())
        
        # Validate XML content
        self.assertTrue(self.planner.validate_xml(result["xml_state"]))

    def test_error_handling(self):
        # Test with empty state
        with self.assertRaises(ValueError):
            self.planner.run({})

if __name__ == '__main__':
    unittest.main() 