from typing import Dict, Any
from langchain_core.messages import HumanMessage
from .base_agent import BaseAgent, ANTHROPIC_SMALL_MODEL
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class CodeReviewAgent(BaseAgent):
    def __init__(self):
        super().__init__(model_name=ANTHROPIC_SMALL_MODEL)
        
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Review the code using the code review agent"""
        logger.info("Starting code review step")
        
        try:
            # Parse the XML project structure
            xml_root = ET.fromstring(state['code'])
            
            # Review each Python file
            file_reviews = []
            for file_elem in xml_root.findall('.//file'):
                filename = file_elem.find('name').text.strip()
                if not filename.endswith('.py'):
                    continue
                    
                content = file_elem.find('content').text.strip()
                review = self._review_file(filename, content, state['execution_result'])
                file_reviews.append((filename, review))
            
            # Combine reviews into single XML
            combined_review = ET.Element('review')
            
            # Determine overall approval based on all file reviews
            all_approved = all(
                "true" in review.lower() and 
                "<approved>true</approved>" in review.lower()
                for _, review in file_reviews
            )
            
            approved_elem = ET.SubElement(combined_review, 'approved')
            approved_elem.text = str(all_approved).lower()
            
            # Add file-specific reviews
            files_elem = ET.SubElement(combined_review, 'files')
            for filename, review in file_reviews:
                try:
                    file_review_elem = ET.fromstring(review)
                    file_elem = ET.SubElement(files_elem, 'file')
                    name_elem = ET.SubElement(file_elem, 'name')
                    name_elem.text = filename
                    
                    # Copy review elements
                    for child in file_review_elem:
                        if child.tag != 'approved':  # Skip individual file approval
                            file_elem.append(child)
                except ET.ParseError:
                    logger.error(f"Error parsing review for {filename}")
                    continue
            
            # Convert to string
            review_xml = ET.tostring(combined_review, encoding='unicode')
            
            logger.info(f"Code review complete. Approved: {all_approved}")
            return {
                "review_result": {"approved": all_approved, "raw_review": review_xml},
                "next": "package" if all_approved else "generate",
            }
            
        except ET.ParseError:
            logger.error("Invalid XML format in code")
            return {
                "review_result": {"approved": False, "raw_review": "Invalid code format"},
                "next": "generate",
            }
        
    def _review_file(self, filename: str, content: str, execution_result: Dict) -> str:
        """Review a single Python file"""
        # Extract relevant execution info for this file
        file_execution_info = self._extract_file_execution_info(filename, execution_result)
        
        prompt = """You are a code review agent. Review the Python code for:
1. Code quality and best practices
2. Potential bugs or issues
3. Security concerns
4. Performance considerations
5. Documentation completeness
6. Module interactions and dependencies
7. Test coverage (if tests are present)

Consider the execution results when reviewing the code. Pay special attention to:
- Any runtime errors or exceptions
- Test failures
- Performance issues
- Module import issues
- Integration problems between modules

Provide your response in XML format like this:
<review>
    <approved>true/false</approved>
    <issues>
        <issue>Issue description 1</issue>
        <issue>Issue description 2</issue>
    </issues>
    <suggestions>
        <suggestion>Suggestion 1</suggestion>
        <suggestion>Suggestion 2</suggestion>
    </suggestions>
    <module_interactions>
        <interaction>Description of how this module interacts with others</interaction>
    </module_interactions>
</review>
"""

        review_message = f"""Review the following Python file ({filename}):

{content}

Execution result for this file:
{file_execution_info}
"""
        
        return self._invoke_model([
            HumanMessage(content=prompt),
            HumanMessage(content=review_message)
        ])

    def _extract_file_execution_info(self, filename: str, execution_result: Dict) -> str:
        """Extract execution information relevant to a specific file"""
        if not execution_result:
            return "No execution results available"
            
        # Initialize the result string
        result_parts = []
        
        # Add execution success/failure
        result_parts.append(f"Execution success: {execution_result.get('success', False)}")
        
        # Process stdout for relevant lines
        if stdout := execution_result.get('stdout', ''):
            relevant_lines = []
            for line in stdout.split('\n'):
                # Look for lines relevant to this file
                if (filename in line or 
                    'test_' + filename in line or
                    self._is_relevant_output(line, filename)):
                    relevant_lines.append(line)
            if relevant_lines:
                result_parts.append("Relevant stdout:")
                result_parts.extend(f"  {line}" for line in relevant_lines)
        
        # Process stderr for relevant lines
        if stderr := execution_result.get('stderr', ''):
            relevant_lines = []
            for line in stderr.split('\n'):
                if (filename in line or 
                    'test_' + filename in line or
                    self._is_relevant_output(line, filename)):
                    relevant_lines.append(line)
            if relevant_lines:
                result_parts.append("Relevant stderr:")
                result_parts.extend(f"  {line}" for line in relevant_lines)
        
        # Add any specific error
        if error := execution_result.get('error'):
            if filename in str(error):
                result_parts.append(f"Error: {error}")
        
        return '\n'.join(result_parts)
    
    def _is_relevant_output(self, line: str, filename: str) -> bool:
        """Determine if an output line is relevant to the file being reviewed"""
        # Remove file extension for matching
        module_name = filename.replace('.py', '')
        
        # Check for various patterns that might indicate relevance
        relevant_patterns = [
            module_name,  # Module name
            f"import {module_name}",  # Import statements
            f"from {module_name}",    # From imports
            "Traceback",              # Error traces
            "Error:",                 # Error messages
            "Warning:",               # Warning messages
            "test_",                  # Test output
            "FAILED",                 # Test failures
            "PASSED",                 # Test passes
            "AssertionError"         # Test assertions
        ]
        
        return any(pattern in line for pattern in relevant_patterns)
