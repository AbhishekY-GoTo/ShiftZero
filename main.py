"""
ShiftZero - Autonomous On-Call Agent

Entry point for running the webhook server.
"""

import sys
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn
from shiftzero.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('shiftzero.log')
    ]
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    settings = get_settings()

    logger.info("🚀 Starting ShiftZero autonomous agent...")
    logger.info(f"   Webhook port: {settings.webhook_port}")
    logger.info(f"   Dry run mode: {settings.dry_run_mode}")
    logger.info(f"   AWS region: {settings.aws_region}")
    logger.info(f"   Bedrock model: {settings.bedrock_model_id}")

    # Run the server
    uvicorn.run(
        "shiftzero.webhook:app",
        host="0.0.0.0",
        port=settings.webhook_port,
        log_level=settings.log_level.lower(),
        reload=True  # Auto-reload on code changes (disable in production)
    )
