from app import create_app, config, setup_database, socketio
import logging.config
import pathlib
import yaml
import sys

logging.config.dictConfig(yaml.safe_load(pathlib.Path('.').joinpath('logging.yaml').read_bytes()))
server = create_app()


def is_debugging():
    gettrace = getattr(sys, 'gettrace', None)
    if gettrace is None:
        return False
    else:
        return gettrace() is not None


# Run the application
if __name__ == '__main__':
    config.DEBUG = is_debugging()
    setup_database(server)  # Ensure database is initialized and upgraded
    socketio.run(app=server, host=config.HOST, debug=config.DEBUG, log_output=True)
