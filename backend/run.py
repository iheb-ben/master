import os
from flask_migrate import init, migrate, upgrade
from app import create_app, socketio
from app import config
from app.logger import setup_logger
from app.connector import db, check_db_session
from app.utils.setup import initialize_database

server = create_app()
logger = setup_logger()


def setup_database():
    """
    Dynamically initialize, migrate, and upgrade the database.
    """
    with server.app_context():
        # Initialize migrations directory if not present
        migrations_path = os.path.join(os.getcwd(), 'migrations')
        if not os.path.exists(migrations_path):
            init()
        # Generate migration script if needed
        migrate(message='Auto-generated migration')
        # Apply migrations
        upgrade()
        initialize_database()
        if check_db_session():
            db.session.commit()


# Run the application
if __name__ == '__main__':
    setup_database()  # Ensure database is initialized and upgraded
    socketio.run(app=server, host=config.HOST, debug=config.DEBUG, log_output=logger)
