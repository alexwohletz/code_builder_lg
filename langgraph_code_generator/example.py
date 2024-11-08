import os
from dotenv import load_dotenv
from code_generator import CodeGeneratorModule
import textwrap

# Load environment variables
load_dotenv()

def main():
    # Initialize the module
    generator = CodeGeneratorModule()

    # Example prompt
    prompt = """
    Create a Python function that:
    Checks to see if a number is a palindrome
    Must be a function that takes an integer as input and returns a boolean
    Should handle cases where the number is negative or the input is not an integer
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
