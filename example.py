import os
from dotenv import load_dotenv
from langgraph_code_generator.orchestration import CodeGeneratorModule
import textwrap

# Load environment variables
load_dotenv()

def main():
    # Initialize the module
    generator = CodeGeneratorModule()

    # Example prompt
    prompt = """
    "Create a function that sorts a list of integers using the bubble sort algorithm"
    """

    # Remove any common leading whitespace from the prompt
    prompt = textwrap.dedent(prompt)

    # Generate the module
    result = generator.generate_module(prompt)

    # Print the results
    if result["success"]:
        # Print formatted results
        print("\n=== Generated Code ===")
        print(result["code"])

        print("\n=== Execution Results ===")
        print(result["formatted_execution"])

        print("\n=== Code Review ===")
        print(result["formatted_review"])

        # Print file location information
        if package_info := result.get("package_info"):
            print(f"\nGenerated code saved to: {package_info['standalone_file']}")
            print(f"Module package created at: {package_info['module_path']}")
    else:
        print("Error:", result.get("error", "Unknown error occurred"))

if __name__ == "__main__":
    main()
