from application import create_app, config, setup_database, socketio
import sys


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
