"""
Logging configuration for the research assistant.
"""

import logging
import sys


def setup_logger(name: str = "research_assistant", level: str = "INFO") -> logging.Logger:
    """Configure and return a logger that outputs to stdout."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "[%(levelname)s %(asctime)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(handler)

    return logger


log = setup_logger()
