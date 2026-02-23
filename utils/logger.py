import logging
import os
import sys

def setup_logger(name="AegisOS", log_file="d:/Ceaser-AI/logs/aegis.log", level=logging.INFO):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # File Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8', errors='replace')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    # Add a filter or wrapper to handle encoding issues in messages before they hit the handler?
    # Python's logging handles most string conversions, but cp1252 console on Windows can fail.
    # We can set the console output to utf-8 if possible, or just let Python handle it.
    # The error in the log was specific to the StreamHandler writing to stdout which might be cp1252.
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger

logger = setup_logger()
