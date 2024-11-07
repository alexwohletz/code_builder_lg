from setuptools import setup, find_packages

# Read requirements from requirements.txt if it exists
try:
    with open('requirements.txt') as f:
        required = f.read().splitlines()
except FileNotFoundError:
    required = [
        'langchain-core',
        'langchain-anthropic',
        'langgraph',
        'e2b',
        'graphviz',  # Optional dependency for visualization
    ]

setup(
    name="langgraph_code_generator",
    version="0.1.0",
    description="A Python code generator using LangGraph and Anthropic's Claude",
    author="Alex", 
    author_email="",
    packages=find_packages(),
    install_requires=required,
    python_requires=">=3.8",  # Based on type annotations usage
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    extras_require={
        'viz': ['graphviz'],  # Optional dependency for visualization
    }
) 