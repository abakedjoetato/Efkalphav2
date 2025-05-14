"""
Check Secrets

This script checks if the required secrets are set.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define required secrets
REQUIRED_SECRETS = [
    {
        "name": "DISCORD_TOKEN",
        "description": "Discord Bot Token",
        "help_text": "You need to create a Discord bot and get its token from the Discord Developer Portal.",
        "required": True
    },
    {
        "name": "MONGODB_URI",
        "description": "MongoDB Connection URI",
        "help_text": "This is needed for database features. If not set, the bot will run without database functionality.",
        "required": False
    }
]

def check_secrets():
    """Check if all required secrets are set"""
    missing_required = []
    missing_optional = []
    
    for secret in REQUIRED_SECRETS:
        name = secret["name"]
        value = os.environ.get(name)
        
        if not value:
            if secret["required"]:
                missing_required.append(secret)
            else:
                missing_optional.append(secret)
    
    return missing_required, missing_optional

def print_missing_secrets(missing_required, missing_optional):
    """Print information about missing secrets"""
    if missing_required:
        logger.error("The following required secrets are missing:")
        for secret in missing_required:
            logger.error(f"- {secret['name']}: {secret['description']}")
            logger.error(f"  {secret['help_text']}")
        print()
    
    if missing_optional:
        logger.warning("The following optional secrets are missing:")
        for secret in missing_optional:
            logger.warning(f"- {secret['name']}: {secret['description']}")
            logger.warning(f"  {secret['help_text']}")
        print()
    
    if missing_required:
        logger.error("Cannot proceed without required secrets!")
        return False
    
    if missing_optional:
        logger.warning("Some features may be unavailable due to missing optional secrets.")
        return True
    
    logger.info("All secrets are properly set.")
    return True

def main():
    """Main function"""
    missing_required, missing_optional = check_secrets()
    
    if print_missing_secrets(missing_required, missing_optional):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())