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
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, END
import textwrap
import xml.etree.ElementTree as ET
from langgraph_code_generator.agents import get_agent, list_agents

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
    return b

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
    attempts: Annotated[int, operator.add]

class CodeGeneratorModule:
    def __init__(self):
        logger.info("Initializing CodeGeneratorModule")
        
        # Initialize agents
        self.agents = {
            name: get_agent(name)
            for name in list_agents()
        }
        
        # Initialize the graph
        logger.info("Creating workflow graph")
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(CodeGenerationState)
        
        # Add nodes for each agent
        logger.info("Adding workflow nodes")
        for agent_name, agent in self.agents.items():
            workflow.add_node(agent_name, agent.run)
        
        # Add edges
        logger.info("Adding workflow edges")
        workflow.add_edge("generate", "generate_sample_data")
        workflow.add_edge("generate_sample_data", "execute")
        
        # Add conditional edges
        def route_after_execute(state: CodeGenerationState) -> str:
            if state["execution_result"].get("success", False):
                return "review"
            if state["attempts"] >= MAX_RETRIES:
                return END
            return "generate"
        
        workflow.add_conditional_edges("execute", route_after_execute)
        
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
            xml_string = review_result.get("raw_review", "")
            # Extract just the XML portion if there's additional content
            if "<?xml" in xml_string:
                xml_part = xml_string[xml_string.find("<?xml"):xml_string.find("</review>") + 9]
            else:
                xml_part = xml_string
                
            root = ET.fromstring(xml_part)
            
            formatted = []
            formatted.append("Code Review Summary:")
            formatted.append("-" * 20)
            
            approved = root.find("approved").text.lower() == "true"
            formatted.append(f"Approved: {'✅ Yes' if approved else '❌ No'}")
            
            issues = root.find("issues")
            if issues is not None and len(issues):
                formatted.append("\nIssues Found:")
                for issue in issues.findall("issue"):
                    formatted.append(f"• {issue.text}")
                    
            suggestions = root.find("suggestions")
            if suggestions is not None and len(suggestions):
                formatted.append("\nSuggestions:")
                for suggestion in suggestions.findall("suggestion"):
                    formatted.append(f"• {suggestion.text}")
                    
            comments = root.find("comments")
            if comments is not None:
                positives = comments.findall("positive")
                if positives:
                    formatted.append("\nPositive Comments:")
                    for positive in positives:
                        formatted.append(f"• {positive.text}")
                        
            return "\n".join(formatted)
        except Exception as e:
            logger.error(f"Error formatting review: {str(e)}")
            logger.debug(f"Raw review content: {review_result.get('raw_review', '')}")
            return f"Error formatting review: {str(e)}\nRaw review:\n{review_result.get('raw_review', '')}"

    def _format_execution_result(self, execution_result: Dict) -> str:
        """Format the execution result into a readable string."""
        formatted = []
        formatted.append("Execution Results:")
        formatted.append("-" * 20)
        
        success = execution_result.get("success", False)
        formatted.append(f"Status: {'✅ Success' if success else '❌ Failed'}")
        
        if stdout := execution_result.get("stdout"):
            formatted.append("\nOutput:")
            if isinstance(stdout, list):
                formatted.extend(str(line) for line in stdout)
            else:
                formatted.append(str(stdout))
                
        if stderr := execution_result.get("stderr"):
            formatted.append("\nErrors:")
            if isinstance(stderr, list):
                formatted.extend(str(line) for line in stderr)
            else:
                formatted.append(str(stderr))
                
        if error := execution_result.get("error"):
            formatted.append("\nError Message:")
            if isinstance(error, list):
                formatted.extend(str(line) for line in error)
            else:
                formatted.append(str(error))
                
        return "\n".join(formatted)

    def generate_module(self, prompt: str) -> Dict[str, Any]:
        """Generate a Python module from a prompt"""
        logger.info("Starting module generation process")
        logger.info(f"Initial prompt: {prompt[:100]}...")
        
        # Remove common leading whitespace
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
            if not result.get("execution_result", {}).get("success", False) or \
               not result.get("review_result", {}).get("approved", False):
                logger.warning("Module generation failed validation checks")
                return {
                    "success": False,
                    "code": result.get("code", ""),
                    "execution_result": result.get("execution_result", {}),
                    "review_result": result.get("review_result", {}),
                    "formatted_execution": self._format_execution_result(
                        result.get("execution_result", {})
                    ),
                    "formatted_review": self._format_review_result(
                        result.get("review_result", {})
                    )
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
            # Cleanup any resources
            for agent in self.agents.values():
                if hasattr(agent, 'cleanup'):
                    agent.cleanup()

    def visualize_workflow(self, output_file: str = "workflow_graph.png") -> None:
        """Generate a visualization of the workflow graph."""
        dot = Digraph(comment="Code Generation Workflow")
        dot.attr(rankdir="LR")
        
        # Add nodes
        nodes = list(self.agents.keys()) + ["END"]
        for node in nodes:
            shape = "doublecircle" if node == "END" else "box"
            dot.node(node, node, shape=shape)
            
        # Add edges
        dot.edge("generate", "generate_sample_data")
        dot.edge("generate_sample_data", "execute")
        
        # Add conditional edges
        dot.edge("execute", "review", color="green", label="success")
        dot.edge("execute", "generate", color="red", label="failure")
        dot.edge("execute", "END", color="blue", label="max retries")
        
        dot.edge("review", "package", color="green", label="approved")
        dot.edge("review", "generate", color="red", label="not approved")
        dot.edge("review", "END", color="blue", label="max retries")
        
        dot.edge("package", "END")
        
        # Save the graph
        dot.render(output_file, format="png", cleanup=True)
        logger.info(f"Workflow graph visualization saved to {output_file}.png")

    def __del__(self):
        """Ensure cleanup happens during garbage collection"""
        for agent in self.agents.values():
            if hasattr(agent, 'cleanup'):
                agent.cleanup()
