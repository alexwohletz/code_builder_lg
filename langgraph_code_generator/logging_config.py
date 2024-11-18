import logging
import os
from datetime import datetime

def configure_logging():
    """Configure logging for the application."""
    # Use a relative path in the current directory or user's home directory
    log_dir = os.path.join(os.getcwd(), 'logs')
    # Alternative: use home directory
    # log_dir = os.path.join(os.path.expanduser('~'), 'code_builder_lg_logs')
    
    os.makedirs(log_dir, exist_ok=True)

    # Generate a unique log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'app_log_{timestamp}.log')

    # Configure logging to output to both file and console
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG level
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),  # Log to file
            logging.StreamHandler()  # Log to console (stdout)
        ]
    )

    # Optionally, set specific loggers to DEBUG level
    logging.getLogger('langgraph_code_generator').setLevel(logging.DEBUG)
    
    # If you want to suppress debug logs from other libraries
    logging.getLogger('httpx').setLevel(logging.INFO)
    logging.getLogger('httpcore').setLevel(logging.INFO)