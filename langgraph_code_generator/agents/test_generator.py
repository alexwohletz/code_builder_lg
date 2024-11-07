from typing import Dict, Any, List, Tuple
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent, ANTHROPIC_SMALL_MODEL
import ast
import logging

logger = logging.getLogger(__name__)

class TestGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(model_name=ANTHROPIC_SMALL_MODEL)
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test cases for the code"""
        logger.info("Starting test case generation step")
        
        existing_test_data = self._extract_test_data(state["messages"][0].content)
        code = state["code"]
        
        function_info = self._analyze_function(code)
        test_code = self._generate_test_code(function_info, code, existing_test_data)
        
        return {
            "test_cases": {"code": test_code, "original_data": existing_test_data},
            "next": "execute",
        }
    
    def _analyze_function(self, code: str) -> Dict[str, Any]:
        try:
            tree = ast.parse(code)
            function_def = next(node for node in ast.walk(tree) 
                              if isinstance(node, ast.FunctionDef))
            
            params = []
            for arg in function_def.args.args:
                param_name = arg.arg
                param_type = (arg.annotation.id 
                            if hasattr(arg, 'annotation') 
                            and hasattr(arg.annotation, 'id') 
                            else None)
                params.append((param_name, param_type))
            
            return {
                "name": function_def.name,
                "params": params
            }
        except Exception as e:
            logger.error(f"Error analyzing function: {e}")
            return {"name": "function", "params": []}
    
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
                          function_info: Dict[str, Any], 
                          code: str, 
                          existing_test_data: str) -> str:
        prompt = f"""Generate simple test code for the following function.
IMPORTANT: 
1. Return ONLY executable Python code
2. DO NOT include any text comments or descriptions
3. Use print statements for test output
4. Include basic assertions
5. Test both valid and invalid inputs
6. Test edge cases appropriate for the function type

Function to test:
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
                return self._generate_fallback_test(
                    function_info["name"], 
                    function_info["params"]
                )
                
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return self._generate_fallback_test(
                function_info["name"], 
                function_info["params"]
            )
    
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
    
    def _generate_fallback_test(self, 
                              function_name: str, 
                              params: List[Tuple[str, str]]) -> str:
        test_values = []
        for _, param_type in params:
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

        return f"""
print("Basic function test")
result = {function_name}({", ".join(test_values)})
print(f"Result: {{result}}")
""" 