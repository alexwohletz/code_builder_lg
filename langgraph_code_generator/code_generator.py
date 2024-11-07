import os
import operator
import logging
from typing import (
    List,
    Dict,
    Any,
    Annotated,
    TypedDict,
)
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from e2b_code_interpreter import Sandbox
from datetime import datetime
import xml.etree.ElementTree as ET
import textwrap
import ast

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

try:
    from graphviz import Digraph
except ImportError:
    logger.warning("Graphviz is not installed. Workflow graph visualization will not be available.")


MAX_RETRIES = 3  # Maximum number of generation attempts


def take_latest_reducer(a: str, b: str) -> str:
    """Reducer that takes the latest value between two strings."""
    return b  # Always take the second (newer) value


def dict_merge_reducer(a: Dict, b: Dict) -> Dict:
    """Reducer that merges two dictionaries, with values from b taking precedence."""
    return {**a, **b}


class CodeGenerationState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    code: Annotated[str, take_latest_reducer]
    test_cases: Annotated[Dict, dict_merge_reducer]
    execution_result: Annotated[Dict, dict_merge_reducer]
    review_result: Annotated[Dict, dict_merge_reducer]
    next: Annotated[str, take_latest_reducer]
    attempts: Annotated[int, operator.add]  # Track number of generation attempts


class CodeGeneratorModule:
    def __init__(self):
        logger.info("Initializing CodeGeneratorModule")

        # Initialize different models for different tasks
        self.generation_model = ChatAnthropic(
            model=os.getenv("ANTHROPIC_LARGE_MODEL", "claude-3-5-sonnet-20241022")
        )
        self.review_model = ChatAnthropic(
            model=os.getenv("ANTHROPIC_LARGE_MODEL", "claude-3-5-sonnet-20241022")
        )
        self.test_model = ChatAnthropic(
            model=os.getenv("ANTHROPIC_SMALL_MODEL", "claude-3-5-haiku-20241022")
        )

        self.sandbox = Sandbox()

        # Initialize the graph
        logger.info("Creating workflow graph")
        self.workflow = self._create_workflow()

    def _generate_code(self, state: CodeGenerationState) -> Dict:
        """Generate code based on the prompt"""
        logger.info("Starting code generation step")

        # Get current attempt count
        attempts = state.get("attempts", 0)

        # Check if we've exceeded max retries
        if attempts >= MAX_RETRIES:
            logger.warning(f"Exceeded maximum retries ({MAX_RETRIES}), ending workflow")
            return {"next": END}

        prompt = """You are a Python code generation agent. Generate ONLY the Python function code.
DO NOT include any explanations, markdown formatting, or backticks.
DO NOT include any text before or after the code.
Start directly with 'def' and end with the last line of code.

If sample data or test cases are provided in the prompt, make sure the function signature 
matches the expected input format.

Requirements:
1. Well-structured and modular
2. Include proper error handling
3. Follow PEP 8 style guidelines
4. Include docstrings
5. Be efficient and maintainable
"""

        # Get the last message from the state
        last_message = state["messages"][-1]
        logger.info(f"Processing user prompt: {last_message.content[:100]}...")

        # Generate code using the larger model
        logger.info(f"Generating code (attempt {attempts + 1}/{MAX_RETRIES})")
        response = self.generation_model.invoke(
            [HumanMessage(content=prompt), last_message]
        )

        # Update state with generated code and increment attempts
        logger.info("Code generation complete")
        return {
            "code": response.content,
            "next": "execute",
            "attempts": attempts + 1,  # Increment the existing count
        }

    def _review_code(self, state: CodeGenerationState) -> Dict:
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
        logger.info("Reviewing code with LLM")
        review_result = self.review_model.invoke(
            [HumanMessage(content=prompt), HumanMessage(content=review_message)]
        )

        # Parse the XML response using string operations
        content = review_result.content
        approved = (
            "true" in content.lower() and "<approved>true</approved>" in content.lower()
        )

        logger.info(f"Code review complete. Approved: {approved}")
        return {
            "review_result": {"approved": approved, "raw_review": content},
            "next": "package" if approved else "generate",
        }

    def _execute_code(self, state: CodeGenerationState) -> Dict:
        """Execute the generated code in the e2b sandbox"""
        logger.info("Starting code execution step")
        try:
            # Clean up test cases before execution
            test_code = state.get("test_cases", {}).get("code", "")
            # Remove any markdown or comment markers
            test_code = test_code.replace("```python", "").replace("```", "")
            # Remove any lines that start with comments or descriptions
            test_code = "\n".join(
                line for line in test_code.splitlines()
                if not (line.strip().startswith(("#", "Here", "Test", "This"))
                       and "print" not in line)
            )
            
            # Combine function code with cleaned test cases
            complete_code = f"{state['code']}\n\n{test_code}"

            # Log the complete code being executed
            logger.info(f"Executing code:\n{complete_code}")

            execution = self.sandbox.run_code(complete_code)
            success = not bool(execution.error)
            logger.info(f"Code execution complete. Success: {success}")

            result = {
                "execution_result": {
                    "success": success,
                    "stdout": execution.logs.stdout,
                    "stderr": execution.logs.stderr,
                    "error": execution.error,
                }
            }

            if success:
                logger.info("Execution successful, proceeding to review")
                result["next"] = "review"
            else:
                logger.warning(f"Execution failed with error: {execution.error}")
                result["next"] = "generate"

            return result

        except Exception as e:
            logger.error(f"Exception during code execution: {str(e)}")
            return {
                "execution_result": {"success": False, "error": str(e)},
                "next": "generate",
            }

    def _extract_test_data(self, prompt: str) -> str:
        """Extract test data section from the prompt if it exists"""
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

    def _package_code(self, state: CodeGenerationState) -> Dict:
        """Package the approved code into a Python module"""
        logger.info("Starting code packaging step")
        try:
            # Create timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Create base directory for all generated modules if it doesn't exist
            base_dir = os.path.join(os.path.dirname(__file__), "generated_modules")
            logger.info(f"Creating {base_dir} directory")
            os.makedirs(base_dir, exist_ok=True)

            # Create timestamped module directory
            module_name = f"generated_module_{timestamp}"
            module_path = os.path.join(base_dir, module_name)
            os.makedirs(module_path, exist_ok=True)

            # Write the code to both a standalone file and the module
            standalone_file = os.path.join(module_path, f"code_generated_{timestamp}.py")
            logger.info(f"Writing code to {standalone_file}")
            with open(standalone_file, "w") as f:
                f.write(state["code"])

            # Write the code to __init__.py in the module directory
            logger.info(f"Writing code to {module_path}/__init__.py")
            with open(os.path.join(module_path, "__init__.py"), "w") as f:
                f.write(state["code"])

            # Create setup.py
            logger.info(f"Creating {module_path}/setup.py")
            setup_content = f"""
from setuptools import setup, find_packages

setup(
    name="{module_name}",
    version="0.1.0",
    packages=find_packages(),
    description="Generated Python module",
)
"""
            with open(os.path.join(module_path, "setup.py"), "w") as f:
                f.write(setup_content)

            logger.info("Code packaging complete")
            return {
                "next": END,
                "package_info": {
                    "standalone_file": os.path.relpath(standalone_file),
                    "module_path": os.path.relpath(module_path),
                },
            }

        except Exception as e:
            logger.error(f"Error during code packaging: {str(e)}")
            return {"next": END}  # End even on error to prevent loops

    def _generate_sample_data(self, state: CodeGenerationState) -> Dict:
        """Generate and format test cases for the code"""
        logger.info("Starting test case generation step")

        # Extract existing test data if provided
        existing_test_data = self._extract_test_data(state["messages"][0].content)

        # Extract function name and signature from the code
        code = state["code"]
        try:
            tree = ast.parse(code)
            function_def = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            function_name = function_def.name
            
            # Analyze parameters
            params = []
            for arg in function_def.args.args:
                param_name = arg.arg
                param_type = arg.annotation.id if hasattr(arg, 'annotation') and hasattr(arg.annotation, 'id') else None
                params.append((param_name, param_type))
            
            logger.info(f"Analyzing function: {function_name} with params: {params}")
        except Exception as e:
            logger.error(f"Error analyzing function signature: {e}")
            function_name = "function"
            params = []

        prompt = f"""Generate simple test code for the following function.
IMPORTANT: 
1. Return ONLY executable Python code
2. DO NOT include any text comments or descriptions
3. Use print statements for test output
4. Include basic assertions
5. Test both valid and invalid inputs
6. Test edge cases appropriate for the function type

Example test structure:
print("Test valid inputs")
result = {function_name}(<valid_input>)
print(f"Input: <input>, Result: {{result}}")
assert <condition>, "Test description"

print("Test error cases")
try:
    {function_name}(<invalid_input>)
    print("Error: Expected exception not raised")
except <ExpectedException>:
    print("Successfully caught expected error")

Function to test:
{code}

Existing test data:
{existing_test_data}
"""

        try:
            # Use the smaller model for test case generation
            response = self.test_model.invoke([HumanMessage(content=prompt)])

            # Clean up the response
            test_code = response.content.strip()
            test_code = test_code.replace("```python", "").replace("```", "")

            # Remove non-code lines while preserving test markers
            test_code = "\n".join(
                line
                for line in test_code.splitlines()
                if (
                    line.strip() 
                    and not line.strip().startswith(("#", "Here", "This", "Note"))
                    or "print" in line
                    or "assert" in line
                    or "try:" in line
                    or "except" in line
                )
            )

            # Validate the test code
            try:
                compile(test_code, '<string>', 'exec')
            except SyntaxError as e:
                logger.error(f"Generated test code has syntax error: {e}")
                # Generate minimal fallback test based on function signature
                fallback_test = self._generate_fallback_test(function_name, params)
                test_code = fallback_test

            logger.info("Test case generation complete")
            return {
                "test_cases": {"code": test_code, "original_data": existing_test_data},
                "next": "execute",
            }
        except Exception as e:
            logger.error(f"Error generating test cases: {str(e)}")
            fallback_test = self._generate_fallback_test(function_name, params)
            return {
                "test_cases": {
                    "code": fallback_test,
                    "original_data": existing_test_data,
                },
                "next": "execute",
            }

    def _generate_fallback_test(self, function_name: str, params: List[tuple]) -> str:
        """Generate minimal fallback test based on function signature"""
        # Generate default test values based on parameter types
        test_values = []
        for param_name, param_type in params:
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
        
        # If no parameters were found, use a simple value
        if not test_values:
            test_values = ['0']

        return f"""
print("Basic function test")
result = {function_name}({", ".join(test_values)})
print(f"Result: {{result}}")
"""

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(CodeGenerationState)

        # Add nodes
        logger.info("Adding workflow nodes")
        workflow.add_node("generate", self._generate_code)
        workflow.add_node("generate_sample_data", self._generate_sample_data)
        workflow.add_node("execute", self._execute_code)
        workflow.add_node("review", self._review_code)
        workflow.add_node("package", self._package_code)

        # Add edges
        logger.info("Adding workflow edges")

        # After generate, go to generate_sample_data
        workflow.add_edge("generate", "generate_sample_data")

        # After generate_sample_data, go to execute
        workflow.add_edge("generate_sample_data", "execute")

        # After execute, conditionally route based on success
        def route_after_execute(state: CodeGenerationState) -> str:
            if state["execution_result"].get("success", False):
                return "review"
            if state["attempts"] >= MAX_RETRIES:
                return END
            return "generate"

        workflow.add_conditional_edges("execute", route_after_execute)

        # After review, conditionally route based on approval
        def route_after_review(state: CodeGenerationState) -> str:
            if state["review_result"].get("approved", False):
                return "package"
            if state["attempts"] >= MAX_RETRIES:
                return END
            return "generate"

        workflow.add_conditional_edges("review", route_after_review)

        # Package always ends the workflow
        workflow.add_edge("package", END)

        # Set entry point
        workflow.set_entry_point("generate")

        return workflow.compile()

    def _format_review_result(self, review_result: Dict) -> str:
        """Format the review result XML into a readable string."""
        try:
            # Get the raw XML review
            xml_string = review_result.get("raw_review", "")

            # Parse the XML
            root = ET.fromstring(xml_string)

            # Format the review
            formatted = []
            formatted.append("Code Review Summary:")
            formatted.append("-" * 20)

            # Add approval status
            approved = root.find("approved").text.lower() == "true"
            formatted.append(f"Approved: {'✅ Yes' if approved else '❌ No'}")

            # Add issues
            issues = root.find("issues")
            if issues is not None and len(issues):
                formatted.append("\nIssues Found:")
                for issue in issues.findall("issue"):
                    formatted.append(f"• {issue.text}")

            # Add suggestions
            suggestions = root.find("suggestions")
            if suggestions is not None and len(suggestions):
                formatted.append("\nSuggestions:")
                for suggestion in suggestions.findall("suggestion"):
                    formatted.append(f"• {suggestion.text}")

            return "\n".join(formatted)
        except Exception as e:
            return f"Error formatting review: {str(e)}\nRaw review:\n{review_result.get('raw_review', '')}"

    def _format_execution_result(self, execution_result: Dict) -> str:
        """Format the execution result into a readable string."""
        formatted = []
        formatted.append("Execution Results:")
        formatted.append("-" * 20)

        # Add execution status
        success = execution_result.get("success", False)
        formatted.append(f"Status: {'✅ Success' if success else '❌ Failed'}")

        # Add stdout if present
        if stdout := execution_result.get("stdout"):
            formatted.append("\nOutput:")
            # Handle both string and list outputs
            if isinstance(stdout, list):
                formatted.extend(str(line) for line in stdout)
            else:
                formatted.append(str(stdout))

        # Add stderr if present
        if stderr := execution_result.get("stderr"):
            formatted.append("\nErrors:")
            # Handle both string and list outputs
            if isinstance(stderr, list):
                formatted.extend(str(line) for line in stderr)
            else:
                formatted.append(str(stderr))

        # Add error if present
        if error := execution_result.get("error"):
            formatted.append("\nError Message:")
            # Handle both string and list outputs
            if isinstance(error, list):
                formatted.extend(str(line) for line in error)
            else:
                formatted.append(str(error))

        return "\n".join(formatted)

    def generate_module(self, prompt: str) -> Dict[str, Any]:
        """Generate a Python module from a prompt"""
        logger.info("Starting module generation process")
        logger.info(f"Initial prompt: {prompt[:100]}...")

        # Remove any common leading whitespace from the prompt
        prompt = textwrap.dedent(prompt)

        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "code": "",
            "test_cases": {},
            "execution_result": {},
            "review_result": {},
            "next": "generate",
            "attempts": 0,
        }

        try:
            logger.info("Invoking workflow")
            result = self.workflow.invoke(initial_state)

            # Check if we actually succeeded
            if not result.get("execution_result", {}).get(
                "success", False
            ) or not result.get("review_result", {}).get("approved", False):
                logger.warning("Module generation failed validation checks")
                return {
                    "success": False,
                    "code": result.get("code", ""),
                    "execution_result": result.get("execution_result", {}),
                    "review_result": result.get("review_result", {}),
                    "formatted_execution": self._format_execution_result(result.get("execution_result", {})),
                    "formatted_review": self._format_review_result(result.get("review_result", {}))
                }

            logger.info("Module generation completed successfully")
            return {
                "success": True,
                "code": result["code"],
                "execution_result": result["execution_result"],
                "review_result": result["review_result"],
                "formatted_execution": self._format_execution_result(result["execution_result"]),
                "formatted_review": self._format_review_result(result["review_result"]),
                "package_info": result.get("package_info", {})
            }
        except Exception as e:
            logger.error(f"Error during module generation: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            logger.info("Cleaning up sandbox")
            self.sandbox.kill()

    def visualize_workflow(self, output_file: str = "workflow_graph.png") -> None:
        """Generate a visualization of the workflow graph.

        Args:
            output_file: Path where the PNG file should be saved
        """
        dot = Digraph(comment="Code Generation Workflow")
        dot.attr(rankdir="LR")  # Left to right layout

        # Add nodes
        nodes = [
            "generate",
            "generate_sample_data",
            "execute",
            "review",
            "package",
            "END",
        ]
        for node in nodes:
            # Use different shape for END node
            shape = "doublecircle" if node == "END" else "box"
            dot.node(node, node, shape=shape)

        # Add edges
        dot.edge("generate", "generate_sample_data")
        dot.edge("generate_sample_data", "execute")

        # Add conditional edges with different colors
        # Execute -> Review (success) or Generate (failure)
        dot.edge("execute", "review", color="green", label="success")
        dot.edge("execute", "generate", color="red", label="failure")
        dot.edge("execute", "END", color="blue", label="max retries")

        # Review -> Package (approved) or Generate (not approved)
        dot.edge("review", "package", color="green", label="approved")
        dot.edge("review", "generate", color="red", label="not approved")
        dot.edge("review", "END", color="blue", label="max retries")

        # Package always ends
        dot.edge("package", "END")

        # Save the graph
        dot.render(output_file, format="png", cleanup=True)
        logger.info(f"Workflow graph visualization saved to {output_file}.png")
