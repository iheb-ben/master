from app import create_app, config, setup_database, socketio
from pathlib import Path
import logging.config
import yaml
import sys

_config_file = Path('.').joinpath('logging.yaml')
if _config_file.is_file():
    logging.config.dictConfig(yaml.safe_load(_config_file.read_bytes()))
logging.getLogger('root').disabled = False


def is_debugging():
    gettrace = getattr(sys, 'gettrace', None)
    if gettrace is None:
        return False
    else:
        return gettrace() is not None


# Run the application
if __name__ == '__main__':
    if is_debugging():
        config.DEBUG = True
    server = create_app()
    setup_database(server)  # Ensure database is initialized and upgraded
    socketio.run(app=server, port=config.PORT, debug=config.DEBUG, log_output=True)
