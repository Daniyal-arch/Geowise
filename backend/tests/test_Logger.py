# Create a simple test script: test_logger.py
from app.utils.logger import setup_logging, get_logger

# Test the logger
setup_logging("development")
logger = get_logger("test_module")

logger.info("Testing GEOWISE logger", 
           bbox=[70.0, 30.0, 80.0, 40.0], 
           h3_resolution=9,
           dataset="NASA_FIRMS")

# Run with: python test_logger.py