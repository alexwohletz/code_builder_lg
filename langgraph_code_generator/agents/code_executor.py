from typing import Dict, Any
from .base_agent import BaseAgent
from e2b_code_interpreter import Sandbox
import logging

logger = logging.getLogger(__name__)

class CodeExecutorAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sandbox = None
    
    @property
    def sandbox(self) -> Sandbox:
        """Lazy initialization of sandbox"""
        if self._sandbox is None:
            self._sandbox = Sandbox()
        return self._sandbox
        
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the generated code in the e2b sandbox"""
        logger.info("Starting code execution step")
        
        try:
            # Clean up test cases
            test_code = state.get("test_cases", {}).get("code", "")
            test_code = self._clean_test_code(test_code)
            
            # Combine function code with cleaned test cases
            complete_code = f"{state['code']}\n\n{test_code}"
            logger.info(f"Executing code:\n{complete_code}")
            
            execution = self.sandbox.run_code(complete_code)
            success = not bool(execution.error)
            logger.info(f"Code execution complete. Success: {success}")
            
            result = {
                "execution_result": {
                    "success": success,
                    "stdout": execution.logs.stdout,
                    "stderr": execution.logs.stderr,
                    "error": execution.error,
                }
            }
            
            if success:
                result["next"] = "review"
            else:
                result["next"] = "generate"
            
            return result
            
        except Exception as e:
            logger.error(f"Exception during code execution: {str(e)}")
            return {
                "execution_result": {"success": False, "error": str(e)},
                "next": "generate",
            }
    
    def _clean_test_code(self, test_code: str) -> str:
        """Clean up test cases before execution"""
        test_code = test_code.replace("```python", "").replace("```", "")
        return "\n".join(
            line for line in test_code.splitlines()
            if not (line.strip().startswith(("#", "Here", "Test", "This"))
                   and "print" not in line)
        )
        
    def cleanup(self):
        """Safe cleanup of sandbox resources"""
        if self._sandbox is not None:
            try:
                logger.info("Cleaning up sandbox")
                self._sandbox.kill()
            except Exception as e:
                logger.warning(f"Error during sandbox cleanup: {e}")
            finally:
                self._sandbox = None
        
    def __del__(self):
        """Ensure cleanup happens during garbage collection"""
        self.cleanup()