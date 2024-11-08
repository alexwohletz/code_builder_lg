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
        prompt = """You are a code review agent. Review the Python code for:
1. Code quality and best practices
2. Potential bugs or issues
3. Security concerns
4. Performance considerations
5. Documentation completeness

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
</review>
"""

        review_message = f"""Review the following Python file ({filename}):

{content}

Execution result:
{execution_result}
"""
        
        return self._invoke_model([
            HumanMessage(content=prompt),
            HumanMessage(content=review_message)
        ])
