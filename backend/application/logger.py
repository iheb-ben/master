import logging
from logging.handlers import RotatingFileHandler
from os import PathLike
from pathlib import Path
from typing import Dict, Optional, Union

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class Logger:
    def __init__(self, name: str, log_file: Optional[str] = None, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        if log_file:
            file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def info(self, message: str):
        self.logger.disabled = False
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.disabled = False
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.disabled = False
        self.logger.error(message)

    def debug(self, message: str):
        self.logger.disabled = False
        self.logger.debug(message)


class LoggerManager:
    def __init__(self, log_file: Union[str, PathLike]):
        self.log_file = Path(log_file).absolute().resolve()
        self.loggers: Dict[str, Logger] = {}

    def get_logger(self, name: str, level: int = logging.INFO) -> Logger:
        if name not in self.loggers:
            self.loggers[name] = Logger(name, str(self.log_file), level)
        return self.loggers[name]

    def remove_logger(self, name: str):
        if name in self.loggers:
            del self.loggers[name]


manager = LoggerManager('../logs/master.log')


def get_logger(*args, **kwargs) -> Logger:
    return manager.get_logger(*args, **kwargs)
