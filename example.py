import os
from dotenv import load_dotenv
from langgraph_code_generator.orchestration import CodeGeneratorOrchestrator
import textwrap
from langgraph_code_generator.logging_config import configure_logging

# Load environment variables
load_dotenv()

def main():
    # Configure logging first
    configure_logging()
    
    # Initialize the module
    orchestrator = CodeGeneratorOrchestrator()

    # Example prompt
    prompt = """
    Create a function that finds a palindrome in a string or integer.
    """

    # Remove any common leading whitespace from the prompt
    prompt = textwrap.dedent(prompt)

    # Generate the module
    result = orchestrator.generate_code(prompt)
    print(result)

if __name__ == "__main__":
    main()
