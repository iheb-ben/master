import logging
from pathlib import Path
from app import config


def setup_logger():
    log_level: int = logging.DEBUG if config.DEBUG else getattr(logging, config.LOG_LEVEL)
    log_file = str(Path('.').joinpath('master.log').absolute().resolve())
    logging.basicConfig(filename=log_file, format=config.LOG_FORMAT, level=log_level, force=True)
