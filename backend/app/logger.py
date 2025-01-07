import logging
import os
from app.config import Config


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(Config.LOG_LEVEL)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(Config.LOG_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
