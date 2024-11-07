# LangGraph Code Generator Module

This module implements a workflow for generating, executing, reviewing, and packaging Python code using LangGraph and E2B.

## Features

- Code generation using LangChain and Anthropic's Claude
- Safe code execution in E2B sandbox environment
- Automated code review
- Python module packaging

## Installation

```bash
git clone https://github.com/awohletz/langgraph_code_generator.git
cd langgraph_code_generator
pip install -e .
```

## Usage

```python
from langgraph_code_generator import CodeGeneratorModule

# Initialize the module
generator = CodeGeneratorModule()

# Generate a module from a prompt
result = generator.generate_module(
    "Create a function that calculates the Fibonacci sequence"
)

# Check the result
if result["success"]:
    print("Generated code:", result["code"])
    print("Execution result:", result["execution_result"])
    print("Review result:", result["review_result"])
else:
    print("Error:", result["error"])
```

or just update the `example.py` file with your own prompt and run it.

```bash
python langgraph_code_generator/example.py
```

## Workflow

1. Code Generation: Takes a prompt and generates Python code
2. Code Execution: Executes the code in an E2B sandbox
3. Code Review: Reviews the code for quality and issues
4. Code Packaging: Creates a Python module from approved code

## Requirements

- Python 3.8+

## Environment Variables

- E2B API key (set as environment variable `E2B_API_KEY`)
- Anthropic API key (set as environment variable `ANTHROPIC_API_KEY`)
- Anthropic large model (set as environment variable `ANTHROPIC_LARGE_MODEL`)
- Anthropic small model (set as environment variable `ANTHROPIC_SMALL_MODEL`)
Update the `.env.example` file with your keys and models and rename it to `.env`.

## Visualization

To visualize the workflow, run `python langgraph_code_generator/visualize_graph.py`.
