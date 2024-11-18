from typing import Dict, Any
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent
import logging
import xml.etree.ElementTree as ET
import os
from datetime import datetime
import io, re
from xml.dom import minidom
from .utils import escape_python_code
logger = logging.getLogger(__name__)

class CodeGeneratorAgent(BaseAgent):
    # TODO: Implement the code generator agent, leveraging the prompts/generator.py file and the BASE_SCHEMA.xml file
    # The code generator agent should take the planning information from the XML and generate the code and tests for each file
    # The code generator agent should also update the XML with the new file information
    pass
