from typing import List, Optional
import logging
from master.core import arguments

# Configuration
log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers: List[logging.Handler] = []


def add_handler(handler: logging.Handler, add_default: bool = True):
    """
    Add a logging handler with optional default configuration.

    :param handler: The logging handler to be added.
    :param add_default: Whether to apply default log level and formatter.
    :raises ValueError: If the handler parameter is missing or invalid.
    """
    if not handler:
        raise ValueError('Parameter "handler" is required')

    if add_default:
        logging_level = arguments.get('logging_level', logging.INFO)  # Fallback to INFO if not set
        handler.setLevel(logging_level)
        handler.setFormatter(logging.Formatter(log_format))

    handlers.append(handler)


def configure_logging():
    """
    Configure logging handlers based on application arguments.
    """
    log_file: Optional[str] = arguments.get('log_file', None)
    logging_level = arguments.get('logging_level', logging.INFO)  # Default to INFO level
    try:
        if log_file and not log_file.isspace():
            add_handler(logging.FileHandler(log_file))
        else:
            add_handler(logging.StreamHandler())
        root_logger = logging.getLogger()  # The root logger
        root_logger.setLevel(logging_level)
        for handler in root_logger.handlers:
            handler.setLevel(logging_level)
            handler.setFormatter(logging.Formatter(log_format))
        for handler in handlers:
            root_logger.addHandler(handler)
    except Exception as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Failed to configure logging: {e}")


# Initialize logging
configure_logging()
