"""
Check Secrets Script

Verifies that the required secrets for the Discord bot are set.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def check_secrets():
    """Check if the required secrets are set"""
    # Load environment variables
    load_dotenv()
    
    # Check Discord token
    discord_token = os.environ.get("DISCORD_TOKEN")
    if not discord_token:
        logger.error("DISCORD_TOKEN is not set. The bot will not be able to connect to Discord.")
        return False
    else:
        logger.info("✅ DISCORD_TOKEN is set")
    
    # Check MongoDB URI
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        logger.error("MONGODB_URI is not set. The bot will not be able to connect to the database.")
        return False
    else:
        logger.info("✅ MONGODB_URI is set")
    
    # All required secrets are set
    logger.info("All required secrets are set. The bot should be able to connect to Discord and MongoDB.")
    return True

if __name__ == "__main__":
    if check_secrets():
        sys.exit(0)
    else:
        sys.exit(1)