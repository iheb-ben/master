from app import create_app, config, setup_database, socketio
from app.logger import setup_logger

server = create_app()

# Run the application
if __name__ == '__main__':
    setup_logger()
    setup_database(server)  # Ensure database is initialized and upgraded
    socketio.run(app=server, host=config.HOST, debug=config.DEBUG, log_output=True)
