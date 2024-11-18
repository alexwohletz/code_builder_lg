import unittest
from pathlib import Path
from langchain_core.messages import HumanMessage
from langgraph_code_generator.agents.code_generator import CodeGeneratorAgent

class TestCodeGeneratorAgent(unittest.TestCase):
    def setUp(self):
        self.generator = CodeGeneratorAgent()
        # Sample XML state that would come from the planner
        self.test_state = {
            "xml_state": """
            <code_project>
                <planning>
                    <requirements>
                        <requirement id="req1">Create a simple calculator.</requirement>
                    </requirements>
                    <modules>
                        <module id="mod1">
                            <name>Calculator</name>
                            <description>Basic arithmetic operations.</description>
                        </module>
                    </modules>
                    <file_structure>
                        <file>
                            <file_name>calculator.py</file_name>
                            <module>Calculator</module>
                            <purpose>Implementation of calculator operations.</purpose>
                        </file>
                    </file_structure>
                </planning>
            </code_project>
            """
        }

    def test_generation_phase(self):
        result = self.generator.run(self.test_state)
        
        # Check if generation was successful
        self.assertTrue(result["generation_result"]["success"])
        
        # Verify XML state was updated
        self.assertIsNotNone(result["xml_state"])
        
        # Check if debug file was created
        generated_file = Path("debug_output") / result["generation_result"]["generated_file"]
        self.assertTrue(generated_file.exists())
        
        # Validate XML content
        self.assertTrue(self.generator.validate_xml(result["xml_state"]))

    def test_error_handling(self):
        # Test with empty state
        with self.assertRaises(ValueError):
            self.generator.run({})

if __name__ == '__main__':
    unittest.main() 