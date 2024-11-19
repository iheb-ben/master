from ..tools.enums import Enum
import logging
from typing import List, Dict, Optional, Union
from .parser import arguments


class LoggerType(Enum):
    CRITICAL = logging.CRITICAL
    FATAL = logging.FATAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    WARN = logging.WARN
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    NOTSET = logging.NOTSET


def add_handler(handler: logging.Handler, add_default: bool = True):
    assert handler, 'Parameter "handler" is required'
    if add_default:
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(log_format))
    handlers.append(handler)


_argument_level: Optional[str] = arguments.configuration.get('log_level', None)
level: int = LoggerType.INFO.value
if not _argument_level or _argument_level.isspace():
    logging.getLogger(__name__).warning(f'"log_level" parameter not defined, switch to "INFO"')
else:
    if _argument_level.upper().strip() in LoggerType.names():
        level = eval(f'LoggerType.{_argument_level.upper().strip()}').value
    else:
        logging.getLogger(__name__).warning(f'Incorrect "log_level" parameter, switch to "INFO"')
log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=level, format=log_format)
handlers: List[logging.Handler] = []
_argument_file: Optional[str] = arguments.configuration.get('log_file', None)
if _argument_file:
    add_handler(logging.FileHandler(_argument_file))
else:
    add_handler(logging.StreamHandler())
loggers: Dict[str, logging.Logger] = {}


def get_logger(name: str, custom_handlers: Optional[Union[List[logging.Handler], logging.Handler]] = None) -> logging.Logger:
    if not name:
        raise ValueError('Parameter "name" is required')
    if name in loggers:
        return loggers[name]
    loggers[name] = logging.getLogger(name)
    if loggers[name].hasHandlers() and (handlers or custom_handlers):
        loggers[name].handlers.clear()
    logger_handlers = handlers
    if custom_handlers:
        if not isinstance(custom_handlers, list):
            custom_handlers = [custom_handlers]
        logger_handlers = custom_handlers
    for handler in logger_handlers:
        loggers[name].addHandler(handler)
    return loggers[name]
