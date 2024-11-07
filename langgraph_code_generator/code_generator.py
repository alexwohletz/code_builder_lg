import os
import operator
import logging
from typing import List, Dict, Any, Annotated, Sequence, TypedDict, Callable
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from langchain.tools import Tool
from langgraph.graph import StateGraph, MessageGraph, END
from langgraph.prebuilt.tool_executor import ToolExecutor
from langchain_core.tools import BaseTool
from e2b_code_interpreter import Sandbox

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
    execution_result: Annotated[Dict, dict_merge_reducer]
    review_result: Annotated[Dict, dict_merge_reducer]
    next: Annotated[str, take_latest_reducer]
    attempts: Annotated[int, operator.add]  # Track number of generation attempts

class CodeGeneratorModule:
    def __init__(self):
        logger.info("Initializing CodeGeneratorModule")
        self.llm = ChatAnthropic(model=os.getenv("ANTHROPIC_SMALL_MODEL"))
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
        
        # Generate code using the LLM
        logger.info(f"Generating code (attempt {attempts + 1}/{MAX_RETRIES})")
        response = self.llm.invoke([
            HumanMessage(content=prompt),
            last_message
        ])
        
        # Update state with generated code and increment attempts
        logger.info("Code generation complete")
        return {
            "code": response.content,
            "next": "execute",
            "attempts": attempts + 1  # Increment the existing count
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
        review_result = self.llm.invoke([
            HumanMessage(content=prompt),
            HumanMessage(content=review_message)
        ])
        
        # Parse the XML response using string operations
        content = review_result.content
        approved = "true" in content.lower() and "<approved>true</approved>" in content.lower()
        
        logger.info(f"Code review complete. Approved: {approved}")
        return {
            "review_result": {
                "approved": approved,
                "raw_review": content
            },
            "next": "package" if approved else "generate"
        }

    def _execute_code(self, state: CodeGenerationState) -> Dict:
        """Execute the generated code in the e2b sandbox"""
        logger.info("Starting code execution step")
        try:
            # Extract test data if provided in the prompt
            test_data = self._extract_test_data(state["messages"][0].content)
            
            # Prepare the complete code with test data
            complete_code = state["code"]
            if test_data:
                complete_code += f"\n\n# Test execution\n{test_data}"
            
            logger.info("Executing code in sandbox")
            execution = self.sandbox.run_code(complete_code)
            success = not bool(execution.error)
            logger.info(f"Code execution complete. Success: {success}")
            
            result = {
                "execution_result": {
                    "success": success,
                    "stdout": execution.logs.stdout,
                    "stderr": execution.logs.stderr,
                    "error": execution.error
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
                "execution_result": {
                    "success": False,
                    "error": str(e)
                },
                "next": "generate"
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
            # Create a new directory for the package
            logger.info("Creating generated_module directory")
            os.makedirs("generated_module", exist_ok=True)
            
            # Write the code to __init__.py
            logger.info("Writing code to __init__.py")
            with open("generated_module/__init__.py", "w") as f:
                f.write(state["code"])
            
            # Create setup.py
            logger.info("Creating setup.py")
            setup_content = f'''
from setuptools import setup, find_packages

setup(
    name="generated_module",
    version="0.1.0",
    packages=find_packages(),
    description="Generated Python module",
)
'''
            with open("generated_module/setup.py", "w") as f:
                f.write(setup_content)
            
            logger.info("Code packaging complete")
            return {"next": END}
            
        except Exception as e:
            logger.error(f"Error during code packaging: {str(e)}")
            return {"next": END}  # End even on error to prevent loops

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(CodeGenerationState)

        # Add nodes
        logger.info("Adding workflow nodes")
        workflow.add_node("generate", self._generate_code)
        workflow.add_node("execute", self._execute_code)
        workflow.add_node("review", self._review_code)
        workflow.add_node("package", self._package_code)

        # Add conditional edges based on execution success and review approval
        logger.info("Adding workflow edges")
        
        # After generate, always go to execute
        workflow.add_edge("generate", "execute")
        
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

    def generate_module(self, prompt: str) -> Dict[str, Any]:
        """Generate a Python module from a prompt"""
        logger.info("Starting module generation process")
        logger.info(f"Initial prompt: {prompt[:100]}...")
        
        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "code": "",
            "execution_result": {},
            "review_result": {},
            "next": "generate",
            "attempts": 0  # Initialize attempt counter
        }
        
        try:
            logger.info("Invoking workflow")
            result = self.workflow.invoke(initial_state)
            logger.info("Module generation completed successfully")
            return {
                "success": True,
                "code": result["code"],
                "execution_result": result["execution_result"],
                "review_result": result["review_result"]
            }
        except Exception as e:
            logger.error(f"Error during module generation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            logger.info("Cleaning up sandbox")
            self.sandbox.kill()
