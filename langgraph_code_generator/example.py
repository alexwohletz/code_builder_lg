import os
from dotenv import load_dotenv
from code_generator import CodeGeneratorModule
from datetime import datetime
import xml.etree.ElementTree as ET
from typing import Dict
import json
import textwrap

# Load environment variables
load_dotenv()

def format_review_result(review_result: Dict) -> str:
    """Format the review result XML into a readable string."""
    try:
        # Get the raw XML review
        xml_string = review_result.get('raw_review', '')
        
        # Parse the XML
        root = ET.fromstring(xml_string)
        
        # Format the review
        formatted = []
        formatted.append("Code Review Summary:")
        formatted.append("-" * 20)
        
        # Add approval status
        approved = root.find('approved').text.lower() == 'true'
        formatted.append(f"Approved: {'✅ Yes' if approved else '❌ No'}")
        
        # Add issues
        issues = root.find('issues')
        if issues is not None and len(issues):
            formatted.append("\nIssues Found:")
            for issue in issues.findall('issue'):
                formatted.append(f"• {issue.text}")
        
        # Add suggestions
        suggestions = root.find('suggestions')
        if suggestions is not None and len(suggestions):
            formatted.append("\nSuggestions:")
            for suggestion in suggestions.findall('suggestion'):
                formatted.append(f"• {suggestion.text}")
        
        return "\n".join(formatted)
    except Exception as e:
        return f"Error formatting review: {str(e)}\nRaw review:\n{review_result.get('raw_review', '')}"

def format_execution_result(execution_result: Dict) -> str:
    """Format the execution result into a readable string."""
    formatted = []
    formatted.append("Execution Results:")
    formatted.append("-" * 20)
    
    # Add execution status
    success = execution_result.get('success', False)
    formatted.append(f"Status: {'✅ Success' if success else '❌ Failed'}")
    
    # Add stdout if present
    if stdout := execution_result.get('stdout'):
        formatted.append("\nOutput:")
        # Handle both string and list outputs
        if isinstance(stdout, list):
            formatted.extend(str(line) for line in stdout)
        else:
            formatted.append(str(stdout))
    
    # Add stderr if present
    if stderr := execution_result.get('stderr'):
        formatted.append("\nErrors:")
        # Handle both string and list outputs
        if isinstance(stderr, list):
            formatted.extend(str(line) for line in stderr)
        else:
            formatted.append(str(stderr))
    
    # Add error if present
    if error := execution_result.get('error'):
        formatted.append("\nError Message:")
        # Handle both string and list outputs
        if isinstance(error, list):
            formatted.extend(str(line) for line in error)
        else:
            formatted.append(str(error))
    
    return "\n".join(formatted)

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
        print(format_execution_result(result["execution_result"]))
        
        print("\n=== Code Review ===")
        print(format_review_result(result["review_result"]))
        
        # Print file location information
        if package_info := result.get("package_info"):
            print(f"\nGenerated code saved to: {package_info['standalone_file']}")
            print(f"Module package created at: {package_info['module_path']}")
    else:
        print("Error:", result.get("error", "Unknown error occurred"))

if __name__ == "__main__":
    main()
