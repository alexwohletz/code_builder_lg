from e2b_code_interpreter import Sandbox
from pathlib import Path
import os
from logging import getLogger

logger = getLogger(__name__)

class CodeSandbox:
    """A code sandbox for running the generated ETL code tests on the E2B platform.
    """
    def __init__(self):

        
        # Try to get E2B API key from multiple possible sources
        api_key = (
            os.getenv("E2B_API_KEY")
        )
        
        if not api_key:
            raise ValueError(
                "E2B API key not found. Please either:\n"
                "1. Set the E2B_API_KEY environment variable\n"
                "2. Add 'e2b_api_key' to your config.yaml\n"
                "3. Add 'api_keys.e2b' to your config.yaml\n"
                "4. Add 'sandbox.api_key' to your config.yaml"
            )
            
        self.sbx = Sandbox(api_key=api_key)

    def _run_code(self, code):
        logger.info("Starting code execution...")
        self.sbx.run_code(code)
        logger.info("Finished code execution.")

    def _run_command(self, command):
        logger.info(f"Running command: {command}")
        result =self.sbx.commands.run(command)
        if result.exit_code != 0:
            raise Exception(f"Command failed with exit code {result.exit_code}: {result.stdout or result.stderr or result.error}")
        logger.info(f"Command output: {result.stdout}")
        logger.info(f"Finished running command: {command}")

    def install_python_packages(self):
        logger.info("Starting Python package installation...")
        self._run_command("pip install -r requirements.txt")
        logger.info("Finished Python package installation.")

    def run_python_tests(self):
        logger.info("Starting Python tests execution...")
        self._run_command('python main.py')
        logger.info("Finished Python tests execution.")

    def install_go_modules(self):
        logger.info("Starting Go module download...")
        self._run_command("go mod download")
        logger.info("Finished Go module download.")

    def run_go_tests(self):
        logger.info("Starting Go tests execution...")
        self._run_command("go test ./...")
        logger.info("Finished Go tests execution.")

    def upload_code_package(self, file_path):
        logger.info(f"Uploading code package from: {file_path}")
        path = Path(file_path)
        
        # Use rglob to get all files recursively, including those in subdirectories
        files = [f for f in path.rglob("*") if f.is_file()]
        
        for file in files:
            try:
                # Calculate relative path to maintain directory structure
                relative_path = file.relative_to(path)
                logger.info(f"Uploading file: {relative_path}")
                
                # Determine if file should be read as binary or text
                if file.suffix in ['.pyc', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip']:
                    with open(file, 'rb') as f:
                        file_data = f.read()
                else:
                    with open(file, 'r', encoding='utf-8') as f:
                        file_data = f.read()
                
                # Write the file data to the sandbox using the relative path
                info = self.sbx.files.write(
                    path=str(relative_path),
                    data=file_data
                )
                logger.info(f"File uploaded: {info}")
            except Exception as e:
                logger.error(f"Error uploading file {file}: {str(e)}")
                raise
        logger.info(f"Finished uploading code package from: {file_path}")
