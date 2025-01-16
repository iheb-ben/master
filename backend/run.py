from os import makedirs
from pathlib import Path
from application import create_app, config, setup_database, socketio
from logging.handlers import RotatingFileHandler
from flask import logging as flask_logging
from datetime import datetime
import logging
import sys


def is_debugging():
    gettrace = getattr(sys, 'gettrace', None)
    if gettrace is None:
        return False
    else:
        return gettrace() is not None


def main():
    if is_debugging() or config.ENV != 'production':
        config.DEBUG = True
    server = create_app()
    logger = flask_logging.create_logger(server)
    logger.setLevel(logging.DEBUG)
    for handler in logger.handlers:
        handler.setLevel(logging.NOTSET)
    if not config.LOG_FOLDER:
        config.LOG_FOLDER = f'../logs'
    filename = f'master_{datetime.utcnow().strftime("%Y_%m_%d")}.log'
    file = Path(config.LOG_FOLDER).joinpath(filename).absolute().resolve()
    if not file.parent.is_dir():
        makedirs(file.parent, exist_ok=True)
    if not file.is_file():
        file.touch()
    file_handler = RotatingFileHandler(file, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    setup_database(server)
    logger.disabled = False
    socketio.run(app=server, port=config.PORT, debug=config.DEBUG, log_output=True)


# Run the application
if __name__ == '__main__':
    main()
