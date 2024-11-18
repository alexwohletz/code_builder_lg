import unittest
from pathlib import Path
from langgraph_code_generator.agents.code_executor import CodeExecutorAgent

class TestCodeExecutorAgent(unittest.TestCase):
    def setUp(self):
        self.executor = CodeExecutorAgent()
        # Sample XML state with a simple Python file and test
        self.test_state = {
            "xml_state": """
            <code_project>
                <generation>
                    <files>
                        <file>
                            <file_name>main.py</file_name>
                            <file_contents>
                                <![CDATA[
                                def add(a, b):
                                    return a + b
                                
                                if __name__ == '__main__':
                                    print(add(2, 2))
                                ]]>
                            </file_contents>
                        </file>
                    </files>
                    <test_suite>
                        <test_files>
                            <test_file>
                                <test_file_name>test_main.py</test_file_name>
                                <test_code>
                                    <![CDATA[
                                    import pytest
                                    from main import add
                                    
                                    def test_add():
                                        assert add(2, 2) == 4
                                    ]]>
                                </test_code>
                            </test_file>
                        </test_files>
                    </test_suite>
                </generation>
            </code_project>
            """
        }

    def test_execution_phase(self):
        result = self.executor.run(self.test_state)
        
        # Check if execution was successful
        self.assertTrue(result["sandbox_result"]["success"])
        
        # Verify debug files were created
        debug_files = list(Path("debug_output").glob("execution_*"))
        self.assertTrue(len(debug_files) > 0)

    def test_error_handling(self):
        # Test with empty state
        with self.assertRaises(ValueError):
            self.executor.run({})

    def tearDown(self):
        self.executor.cleanup()

if __name__ == '__main__':
    unittest.main() 