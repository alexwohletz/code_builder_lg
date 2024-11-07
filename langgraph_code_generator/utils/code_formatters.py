import xml.etree.ElementTree as ET
from typing import Dict
import logging

logger = logging.getLogger(__name__)

def format_review_result(review_result: Dict) -> str:
    """Format the review result XML into a readable string."""
    try:
            xml_string = review_result.get("raw_review", "")
            # Extract just the XML portion if there's additional content
            if "<?xml" in xml_string:
                xml_part = xml_string[xml_string.find("<?xml"):xml_string.find("</review>") + 9]
            else:
                xml_part = xml_string
                
            root = ET.fromstring(xml_part)
            
            formatted = []
            formatted.append("Code Review Summary:")
            formatted.append("-" * 20)
            
            approved = root.find("approved").text.lower() == "true"
            formatted.append(f"Approved: {'✅ Yes' if approved else '❌ No'}")
            
            issues = root.find("issues")
            if issues is not None and len(issues):
                formatted.append("\nIssues Found:")
                for issue in issues.findall("issue"):
                    formatted.append(f"• {issue.text}")
                    
            suggestions = root.find("suggestions")
            if suggestions is not None and len(suggestions):
                formatted.append("\nSuggestions:")
                for suggestion in suggestions.findall("suggestion"):
                    formatted.append(f"• {suggestion.text}")
                    
            comments = root.find("comments")
            if comments is not None:
                positives = comments.findall("positive")
                if positives:
                    formatted.append("\nPositive Comments:")
                    for positive in positives:
                        formatted.append(f"• {positive.text}")
                        
            return "\n".join(formatted)
    except Exception as e:
            logger.error(f"Error formatting review: {str(e)}")
            logger.debug(f"Raw review content: {review_result.get('raw_review', '')}")
            return f"Error formatting review: {str(e)}\nRaw review:\n{review_result.get('raw_review', '')}"

def format_execution_result(execution_result: Dict) -> str:
    """Format the execution result into a readable string."""
    formatted = []
    formatted.append("Execution Results:")
    formatted.append("-" * 20)
    
    success = execution_result.get("success", False)
    formatted.append(f"Status: {'✅ Success' if success else '❌ Failed'}")
        
    if stdout := execution_result.get("stdout"):
        formatted.append("\nOutput:")
        if isinstance(stdout, list):
            formatted.extend(str(line) for line in stdout)
        else:
            formatted.append(str(stdout))
            
    if stderr := execution_result.get("stderr"):
        formatted.append("\nErrors:")
        if isinstance(stderr, list):
            formatted.extend(str(line) for line in stderr)
        else:
            formatted.append(str(stderr))
            
    if error := execution_result.get("error"):
        formatted.append("\nError Message:")
        if isinstance(error, list):
            formatted.extend(str(line) for line in error)
    else:
        formatted.append(str(error))
            
    return "\n".join(formatted)