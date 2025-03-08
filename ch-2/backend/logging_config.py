import logging
import sys
import os

def setup_logging():
    """Configure detailed logging for better troubleshooting"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler with color formatting for development
            logging.StreamHandler(sys.stdout),
            # File handler for persistent logs
            logging.FileHandler("logs/app.log")
        ]
    )
    
    # Set specific loggers to more appropriate levels
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Create a specific logger for API calls that will show in console
    api_logger = logging.getLogger("api.calls")
    api_logger.setLevel(logging.INFO)
    
    # Add a file handler specifically for model API calls for debugging
    model_api_handler = logging.FileHandler("logs/model_api_calls.log")
    model_api_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - MODEL: %(message)s'
    ))
    
    model_logger = logging.getLogger("model.api")
    model_logger.setLevel(logging.DEBUG)
    model_logger.addHandler(model_api_handler)
    
    # Return the configured loggers
    return {
        "main": logging.getLogger("app"),
        "api": api_logger,
        "model": model_logger
    }
