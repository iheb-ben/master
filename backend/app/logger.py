import logging
import os
from app import config


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(config.LOG_LEVEL)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(config.LOG_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
