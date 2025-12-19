"""Logging utilities."""

import logging


def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__)
        level: Optional logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    if level is None:
        level = logging.INFO

    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
