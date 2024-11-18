import logging

def configure_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG level
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Optionally, set specific loggers to DEBUG level
    logging.getLogger('langgraph_code_generator').setLevel(logging.DEBUG)
    
    # If you want to suppress debug logs from other libraries
    logging.getLogger('httpx').setLevel(logging.INFO)
    logging.getLogger('httpcore').setLevel(logging.INFO) 