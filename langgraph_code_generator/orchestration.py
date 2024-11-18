import logging
from typing import Annotated, TypedDict, Dict, List
import operator
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, END

# Configure logging with a more detailed format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def take_latest_reducer(a: str, b: str) -> str:
    """Reducer that takes the latest value."""
    return b

def dict_merge_reducer(a: Dict, b: Dict) -> Dict:
    """Reducer that merges dictionaries."""
    return {**a, **b}

class CodeGenerationState(TypedDict):
    """State management for the code generation workflow."""
    messages: Annotated[List[BaseMessage], operator.add]
    xml_state: Annotated[str, take_latest_reducer]  # Current XML state
    run_timestamp: Annotated[str, take_latest_reducer]  # Shared timestamp for debug outputs
    planning_result: Annotated[Dict, dict_merge_reducer]
    generation_result: Annotated[Dict, dict_merge_reducer]
    sandbox_result: Annotated[Dict, dict_merge_reducer]
    iteration_result: Annotated[Dict, dict_merge_reducer]
    package_result: Annotated[Dict, dict_merge_reducer]
    attempts: Annotated[int, operator.add]

class CodeGeneratorOrchestrator:
    """Orchestrates the code generation workflow using LangGraph."""
    
    def __init__(self, max_retries: int = 3):
        logger.info("Initializing CodeGeneratorOrchestrator")
        self.max_retries = max_retries
        
        # Initialize agents (lazy loading)
        self._planner = None
        self._generator = None
        self._sandbox = None
        self._iterator = None
        self._packager = None
        
        # Create workflow
        self.workflow = self._create_workflow()
    
    def _get_planner(self):
        """Lazy load the planner agent."""
        if not self._planner:
            from langgraph_code_generator.agents import get_agent
            self._planner = get_agent('planner')
        return self._planner

    def _get_generator(self):
        """Lazy load the generator agent."""
        if not self._generator:
            from langgraph_code_generator.agents import get_agent
            self._generator = get_agent('generator')
        return self._generator

    def _get_sandbox(self):
        """Lazy load the sandbox agent."""
        if not self._sandbox:
            from langgraph_code_generator.agents import get_agent
            self._sandbox = get_agent('sandbox')
        return self._sandbox

    def _get_iterator(self):
        """Lazy load the iterator agent."""
        if not self._iterator:
            from langgraph_code_generator.agents import get_agent
            self._iterator = get_agent('iterator')
        return self._iterator

    def _get_packager(self):
        """Lazy load the packager agent."""
        if not self._packager:
            from langgraph_code_generator.agents import get_agent
            self._packager = get_agent('packager')
        return self._packager

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow based on the diagram."""
        logger.info("Creating workflow graph")
        workflow = StateGraph(CodeGenerationState)
        
        # Add nodes
        workflow.add_node("plan", self._get_planner().run)
        workflow.add_node("generate", self._get_generator().run)
        workflow.add_node("sandbox", self._get_sandbox().run)
        workflow.add_node("iterate", self._get_iterator().run)
        workflow.add_node("package", self._get_packager().run)
        
        # Add edges following the graph flow
        workflow.add_edge("plan", "generate")
        workflow.add_edge("generate", "sandbox")
        
        # Add conditional edges
        def route_after_sandbox(state: CodeGenerationState) -> str:
            logger.info("Routing after sandbox execution")
            if state["sandbox_result"].get("success", False):
                return "package"
            if state["attempts"] >= self.max_retries:
                logger.warning("Max retries reached, ending workflow")
                return END
            return "iterate"
        
        def route_after_iterate(state: CodeGenerationState) -> str:
            logger.info("Routing after iteration")
            return "generate"
        
        workflow.add_conditional_edges("sandbox", route_after_sandbox)
        workflow.add_conditional_edges("iterate", route_after_iterate)
        
        # Package ends the workflow
        workflow.add_edge("package", END)
        
        # Set entry point
        workflow.set_entry_point("plan")
        
        return workflow.compile()

    def generate_code(self, prompt: str) -> Dict:
        """Generate code from a prompt."""
        logger.info(f"Starting code generation from prompt: {prompt[:100]}...")
        
        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "xml_state": "",  # Will be populated by planner
            "run_timestamp": "",  # Will be populated by planner
            "planning_result": {},
            "generation_result": {},
            "sandbox_result": {},
            "iteration_result": {},
            "package_result": {},
            "attempts": 0
        }
        
        try:
            logger.info("Invoking workflow")
            result = self.workflow.invoke(initial_state)
            
            success = result["sandbox_result"].get("success", False)
            logger.info(f"Workflow completed. Success: {success}")
            
            return {
                "success": success,
                "xml_state": result["xml_state"],
                "run_timestamp": result["run_timestamp"],
                "planning_result": result["planning_result"],
                "generation_result": result["generation_result"],
                "sandbox_result": result["sandbox_result"],
                "package_result": result.get("package_result", {}) if success else {},
            }
            
        except Exception as e:
            logger.error(f"Error during code generation: {str(e)}")
            return {"success": False, "error": str(e)}
        
    def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up resources")
        agents = [
            self._planner, self._generator, self._sandbox,
            self._iterator, self._packager
        ]
        for agent in agents:
            if agent and hasattr(agent, 'cleanup'):
                agent.cleanup()

    def __del__(self):
        """Ensure cleanup on deletion."""
        self.cleanup()
