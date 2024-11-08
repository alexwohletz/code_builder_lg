from typing import Dict, Any, List, Tuple
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent, ANTHROPIC_SMALL_MODEL
import ast
import logging
import xml.etree.ElementTree as ET
from io import StringIO

logger = logging.getLogger(__name__)

class TestGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(model_name=ANTHROPIC_SMALL_MODEL)
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test cases for the code"""
        logger.info("Starting test case generation step")
        
        existing_test_data = self._extract_test_data(state["messages"][0].content)
        
        try:
            # Parse the XML project structure
            xml_root = ET.fromstring(state["code"])
            
            # Create test files for each Python file
            test_files = {}
            for file_elem in xml_root.findall('.//file'):
                filename = file_elem.find('name').text.strip()
                if not filename.endswith('.py'):
                    continue
                    
                content = file_elem.find('content').text.strip()
                test_filename = f"test_{filename}"
                
                # Generate tests for this file
                function_info = self._analyze_file(content)
                test_code = self._generate_test_code(
                    function_info,
                    content,
                    existing_test_data,
                    filename
                )
                test_files[test_filename] = test_code
            
            # Create XML structure for test files
            test_project = ET.Element('project')
            files_elem = ET.SubElement(test_project, 'files')
            
            for filename, content in test_files.items():
                file_elem = ET.SubElement(files_elem, 'file')
                name_elem = ET.SubElement(file_elem, 'name')
                name_elem.text = filename
                content_elem = ET.SubElement(file_elem, 'content')
                content_elem.text = content
            
            # Convert to string
            test_xml = ET.tostring(test_project, encoding='unicode')
            
            return {
                "test_cases": {
                    "code": test_xml,
                    "original_data": existing_test_data
                },
                "next": "execute",
            }
            
        except ET.ParseError:
            logger.error("Invalid XML format in code")
            return {
                "test_cases": {"code": "", "original_data": ""},
                "next": "execute",
            }
    
    def _analyze_file(self, code: str) -> Dict[str, Any]:
        """Analyze a Python file and extract function information"""
        try:
            tree = ast.parse(code)
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    params = []
                    for arg in node.args.args:
                        param_name = arg.arg
                        param_type = (arg.annotation.id 
                                    if hasattr(arg, 'annotation') 
                                    and hasattr(arg.annotation, 'id') 
                                    else None)
                        params.append((param_name, param_type))
                    
                    functions.append({
                        "name": node.name,
                        "params": params
                    })
            
            return {
                "functions": functions
            }
        except Exception as e:
            logger.error(f"Error analyzing file: {e}")
            return {"functions": []}
    
    def _extract_test_data(self, prompt: str) -> str:
        test_markers = [
            ("TEST DATA:", ""),
            ("SAMPLE DATA:", ""),
            ("TEST CASES:", ""),
            ("```python", "```"),
        ]

        for start_marker, end_marker in test_markers:
            if start_marker in prompt:
                start_idx = prompt.find(start_marker) + len(start_marker)
                if end_marker:
                    end_idx = prompt.find(end_marker, start_idx)
                    if end_idx == -1:
                        end_idx = None
                else:
                    end_idx = None
                return prompt[start_idx:end_idx].strip()

        return ""
    
    def _generate_test_code(self, 
                          file_info: Dict[str, Any], 
                          code: str,
                          existing_test_data: str,
                          filename: str) -> str:
        prompt = f"""Generate test code for the following Python file.
IMPORTANT: 
1. Return ONLY executable Python test code
2. DO NOT include any text comments or descriptions
3. Use print statements to show test progress and results
4. Include basic assertions to verify correctness
5. Test both valid and invalid inputs
6. Test edge cases appropriate for each function
7. Include proper imports if needed

File to test ({filename}):
{code}

Existing test data:
{existing_test_data}
"""
        
        try:
            test_code = self._invoke_model([HumanMessage(content=prompt)])
            test_code = self._clean_test_code(test_code)
            
            # Validate the test code
            try:
                compile(test_code, '<string>', 'exec')
                return test_code
            except SyntaxError:
                return self._generate_fallback_tests(file_info["functions"])
                
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return self._generate_fallback_tests(file_info["functions"])
    
    def _clean_test_code(self, test_code: str) -> str:
        test_code = test_code.replace("```python", "").replace("```", "")
        return "\n".join(
            line for line in test_code.splitlines()
            if (line.strip() 
                and not line.strip().startswith(("#", "Here", "This", "Note"))
                or "print" in line
                or "assert" in line
                or "try:" in line
                or "except" in line)
        )
    
    def _generate_fallback_tests(self, functions: List[Dict[str, Any]]) -> str:
        """Generate basic tests for a list of functions"""
        test_code = []
        
        for func in functions:
            test_values = []
            for _, param_type in func["params"]:
                if param_type == 'int':
                    test_values.append('0')
                elif param_type == 'str':
                    test_values.append('"test"')
                elif param_type == 'float':
                    test_values.append('0.0')
                elif param_type == 'bool':
                    test_values.append('True')
                elif param_type == 'list':
                    test_values.append('[]')
                elif param_type == 'dict':
                    test_values.append('{}')
                else:
                    test_values.append('None')
            
            if not test_values:
                test_values = ['0']

            test_code.append(f"""
print("Testing {func['name']} - Basic test")
try:
    result = {func['name']}({", ".join(test_values)})
    print(f"Result: {{result}}")
    assert result is not None, "Function returned None"
    print("{func['name']} - Basic test passed")
except Exception as e:
    print(f"{func['name']} - Basic test failed: {{e}}")
""")
        
        return "\n".join(test_code)
