from typing import Dict, Any, List, Tuple
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent, DEFAULT_MODEL
import ast
import logging
import re
import xml.etree.ElementTree as ET
from io import StringIO
from .utils import unescape_python_code

logger = logging.getLogger(__name__)

class TestGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(model_name=DEFAULT_MODEL)
    
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
                # Unescape the content before processing
                content = unescape_python_code(content)
                test_filename = f"test_{filename}"
                
                # Validate the Python file syntax first
                syntax_check_result = self._validate_python_syntax(content)
                if syntax_check_result is not None:
                    # If syntax error, return the error details
                    return {
                        "test_cases": {
                            "code": "",
                            "original_data": existing_test_data,
                            "syntax_error": syntax_check_result
                        },
                        "next": "test_generation",  # Send back to test generation
                    }
                
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
    
    def _validate_python_syntax(self, code: str) -> Dict[str, Any] | None:
        """
        Validate Python syntax and return error details if syntax is invalid.
        
        Returns:
        - None if syntax is valid
        - Dict with error details if syntax is invalid
        """
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return {
                "error_type": "SyntaxError",
                "message": str(e),
                "filename": e.filename or "<unknown>",
                "lineno": e.lineno,
                "offset": e.offset,
                "text": e.text
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
        # Get module name from filename
        module_name = filename.replace('.py', '')
        
        prompt = rf"""Generate test code for the following Python file.
IMPORTANT: 
1. Return ONLY executable Python test code
2. DO NOT include any text comments or descriptions
3. Use print statements to show test progress and results
4. Include basic assertions to verify correctness
5. Test both valid and invalid inputs
6. Test edge cases appropriate for each function
7. DO NOT include any imports - necessary imports are already in the file
8. DO NOT include 'if __name__ == "__main__"' block - the code will be placed in an existing one
9. DO NOT import {module_name} or its contents - the code being tested is in the same file

File to test ({filename}):
{code}

Existing test data:
{existing_test_data}
"""
        
        try:
            test_code = self._invoke_model([HumanMessage(content=prompt)])
            test_code = self._clean_test_code(test_code)
            
            # Thoroughly remove any main block declarations
            test_code = self._remove_main_blocks(test_code)
            
            # Remove any imports from the generated code
            test_code = self._remove_imports(test_code)
            
            # Ensure the test code is properly indented
            test_code = self._indent_code(test_code)
            
            # Wrap the test code in a single main block
            test_code = f"\nif __name__ == '__main__':\n{test_code}"
            
            # Validate and clean the test code
            cleaned_test_code = self._sanitize_test_code(test_code)
            
            return cleaned_test_code
                
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return ""
    
    def _sanitize_test_code(self, test_code: str, max_attempts: int = 3) -> str:
        """
        Attempt to sanitize test code by progressively cleaning and validating.
        
        Args:
            test_code (str): The test code to sanitize
            max_attempts (int): Maximum number of sanitization attempts
        
        Returns:
            str: Sanitized test code or empty string if unable to sanitize
        """
        for attempt in range(max_attempts):
            try:
                # Compile the code to check for syntax errors
                compile(test_code, '<string>', 'exec')
                return test_code
            except SyntaxError:
                # Progressive cleanup strategies
                if attempt == 0:
                    # Remove duplicate or nested main blocks
                    test_code = self._remove_nested_main_blocks(test_code)
                elif attempt == 1:
                    # Remove any remaining problematic constructs
                    test_code = self._remove_problematic_constructs(test_code)
                elif attempt == 2:
                    # Last resort: strip down to bare minimum
                    test_code = self._minimal_test_code(test_code)
        
        logger.warning("Unable to sanitize test code after multiple attempts")
        return ""
    
    def _remove_nested_main_blocks(self, code: str) -> str:
        """Remove nested or multiple main blocks, keeping only the outermost."""
        # Remove all but the first main block
        main_block_pattern = r'(if\s+__name__\s*==\s*[\'"]__main__[\'"]:\s*)'
        matches = list(re.finditer(main_block_pattern, code))
        
        if len(matches) > 1:
            # Keep only the first main block, remove others
            first_main_block = matches[0].start()
            last_main_block = matches[-1].end()
            
            # Extract the content of the last main block
            last_block_content = code[last_main_block:]
            
            # Reconstruct the code with only the first main block
            code = code[:first_main_block] + f"if __name__ == '__main__':\n{last_block_content}"
        
        return code
    
    def _remove_problematic_constructs(self, code: str) -> str:
        """Remove potentially problematic code constructs."""
        # Remove multiple consecutive main blocks
        code = re.sub(r'(if\s+__name__\s*==\s*[\'"]__main__[\'"]:\s*)+', 
                      r'if __name__ == \'__main__\':\n', code)
        
        # Remove any duplicate function definitions
        seen_functions = set()
        cleaned_lines = []
        for line in code.splitlines():
            if re.match(r'def\s+(\w+)\s*\(', line):
                func_name = re.match(r'def\s+(\w+)\s*\(', line).group(1)
                if func_name not in seen_functions:
                    seen_functions.add(func_name)
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _minimal_test_code(self, code: str) -> str:
        """Generate a minimal test code structure."""
        # Extract function names from the original code
        function_names = re.findall(r'def\s+(\w+)\s*\(', code)
        
        # Create a minimal test structure
        minimal_tests = []
        for func in function_names:
            minimal_tests.append("""    def test_{0}():
        print("Minimal test for {0}")
        assert True  # Placeholder assertion
""".format(func))
        
        # If no functions found, add a placeholder test
        if not minimal_tests:
            minimal_tests.append("""    def test_placeholder():
        print("No specific tests generated")
        assert True  # Placeholder assertion
""")
        
        return """
if __name__ == '__main__':
{0}
""".format('\n'.join(minimal_tests))
    
    def _clean_test_code(self, test_code: str) -> str:
        # Remove code block markers
        test_code = test_code.replace("```python", "").replace("```", "")
        
        # Remove lines that are comments or non-executable text
        cleaned_lines = []
        for line in test_code.splitlines():
            stripped_line = line.strip()
            if (stripped_line and 
                not stripped_line.startswith(("#", "Here", "This", "Note", "Explanation")) and
                not stripped_line.startswith(("'''", '"""')) and
                not stripped_line.endswith(("'''", '"""'))):
                cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines)

    def _indent_code(self, code: str, spaces: int = 4) -> str:
        """Indent code block by specified number of spaces."""
        lines = code.splitlines()
        indented_lines = [' ' * spaces + line if line.strip() else line 
                         for line in lines]
        return '\n'.join(indented_lines)

    def _remove_main_blocks(self, code: str) -> str:
        """Remove any if __name__ == '__main__' blocks while keeping their content."""
        lines = code.splitlines()
        result = []
        skip_block = False
        block_indent = 0
        
        for line in lines:
            stripped_line = line.strip()
            current_indent = len(line) - len(line.lstrip())
            
            # Check for main block start
            if stripped_line.startswith('if __name__ == ') and ('__main__' in stripped_line):
                skip_block = True
                block_indent = current_indent
                continue
            
            # If we're in a skipped block, only keep lines with deeper indentation
            if skip_block:
                if current_indent > block_indent:
                    result.append(line)
                else:
                    skip_block = False
            
            # If not in a skipped block, keep the line
            if not skip_block:
                result.append(line)
        
        return '\n'.join(result)

    def _remove_imports(self, code: str) -> str:
        """Remove any import statements from the code."""
        lines = code.splitlines()
        return '\n'.join(
            line for line in lines 
            if not line.strip().startswith(('import ', 'from '))
        )
