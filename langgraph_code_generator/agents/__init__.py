from typing import Dict, Type
from .base_agent import BaseAgent
from .code_generator import CodeGeneratorAgent
from .code_reviewer import CodeReviewAgent
from .code_executor import CodeExecutorAgent
from .code_packager import CodePackagerAgent
from .test_generator import TestGeneratorAgent

# Registry of all available agents
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "generate": CodeGeneratorAgent,
    "generate_sample_data": TestGeneratorAgent,
    "execute": CodeExecutorAgent,
    "review": CodeReviewAgent,
    "package": CodePackagerAgent,
}

def get_agent(agent_name: str, **kwargs) -> BaseAgent:
    """Factory function to create agent instances"""
    if agent_name not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_name}")
    
    return AGENT_REGISTRY[agent_name](**kwargs)

def list_agents() -> list:
    """Return list of available agent names"""
    return list(AGENT_REGISTRY.keys()) 