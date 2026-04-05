"""
Main entry point for the Crypto Trading Bot
Combines trading engine with GUI
"""
import logging
from gui import main as launch_gui
from config import get_logger

logger = get_logger(__name__)


def main():
    """Launch the complete application"""
    logger.info("=" * 60)
    logger.info("Starting Crypto Trading Bot - Advanced Edition")
    logger.info("=" * 60)
    
    try:
        launch_gui()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")


if __name__ == "__main__":
    main()