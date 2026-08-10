import logging
import datetime as dt
from typing import Literal
from quick_wins.config import LOG_DIR


def get_logger(
    name: str,
    logging_level_str: Literal["debug", "info", "warn", "error", "critical"] = "info",
) -> logging.Logger:
    """
    Create and configure a reusable logger instance with file and console output.

    This function:
    - Maps a string-based logging level to the corresponding `logging` constant
    - Configures a logger with consistent formatting
    - Adds both file and stream handlers (if not already present)
    - Ensures idempotent initialisation (no duplicate handlers)

    Args:
        name (str):
            Name of the logger, typically `__name__` of the calling module or class.
        logging_level_str (Literal["debug", "info", "warn", "error", "critical"], optional):
            Logging verbosity level. Defaults to "info".

    Returns:
        logging.Logger:
            Configured logger instance.

    Raises:
        ValueError:
            If `logging_level_str` is not one of the supported logging levels.

    Notes:
        - Log format:
          "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        - File logs are written to:
          LOG_DIR / "<YYYY-MM-DD>.log"
        - Handlers are added only once per logger instance to prevent duplicate logs.
        - A startup message is emitted indicating the configured logging level.
        - Designed for consistent use across data ingestion and processing classes
          (e.g. ExcelReader, XMLReader).
    """

    logger = logging.getLogger(name)

    logging_dict = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARN,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    if not (logging_level_int := logging_dict.get(logging_level_str.lower())):
        raise ValueError(
            f'Expected "logging_level_str" to be any of {logging_dict.keys()}, got "{logging_level_str}" instead'
        )

    if not logger.handlers:
        # Add formatting and config basic level
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        logger.setLevel(logging_level_int)

        # Add FileHandler
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        fhandler = logging.FileHandler(LOG_DIR / f"{dt.date.today()}.log")
        fhandler.setFormatter(formatter)
        logger.addHandler(fhandler)

        # Add StreamHandler
        shandler = logging.StreamHandler()
        shandler.setFormatter(formatter)
        logger.addHandler(shandler)

        # Initial message
        logger.log(logging_level_int, f"Logging level set to {logging_level_str}")

    return logger
