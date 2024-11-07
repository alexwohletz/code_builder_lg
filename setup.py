from setuptools import setup, find_packages

setup(
    name="langgraph_code_generator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain",
        "langchain-anthropic",
        "langgraph",
        "e2b",
        "graphviz",
    ],
) 