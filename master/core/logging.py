from typing import Optional
import logging
from master.core import arguments
import threading

# Configuration
log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
_lock = threading.Lock()  # Ensure thread-safe logging setup


def add_handler(handler: logging.Handler, add_default: bool = True):
    """
    Add a logging handler to the root logger with optional default configuration.

    :param handler: The logging handler to be added.
    :param add_default: Whether to apply default log level and formatter.
    :raises ValueError: If the handler parameter is missing or invalid.
    """
    if not handler:
        raise ValueError('Parameter "handler" is required')
    if add_default:
        logging_level: int = arguments['logging_level']
        handler.setLevel(logging_level)
        handler.setFormatter(logging.Formatter(log_format))
    with _lock:
        root_logger = logging.getLogger()
        if handler not in root_logger.handlers:
            root_logger.addHandler(handler)


def _apply_handler_config(handler: logging.Handler, level: int, formatter: logging.Formatter):
    """
    Apply configuration to a logging handler.

    :param handler: The logging handler to configure.
    :param level: Logging level to set.
    :param formatter: Formatter to apply.
    """
    handler.setLevel(level)
    handler.setFormatter(formatter)


def configure_logging():
    """
    Configure logging for the application based on arguments.
    Updates the root logger and ensures consistent configuration across all handlers.
    """
    logging_level: int = arguments['logging_level']
    with _lock:
        try:
            root_logger = logging.getLogger()
            root_logger.setLevel(logging_level)
            formatter = logging.Formatter(log_format)
            for handler in root_logger.handlers:
                _apply_handler_config(handler, logging_level, formatter)
        except Exception as e:
            logging.basicConfig(level=logging.ERROR)
            logging.error(f"Failed to configure logging: {e}")
    log_file: str = arguments['log_file']
    if log_file and not log_file.isspace():
        add_handler(logging.FileHandler(log_file))
    else:
        add_handler(logging.StreamHandler())


# Initialize logging
configure_logging()
