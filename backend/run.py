import datetime
import functools
import os
from typing import Optional
from flask import request
from flask_migrate import init, migrate, upgrade
from app import create_app, socketio
from app import config, api
from app.connector import db, check_db_session
from app.logger import setup_logger
from app.models.session import Session
from app.models.user import User
from app.tools import client_public_ip
from app.utils.setup import initialize_database, PUBLIC_USER_ID

app = create_app()
logger = setup_logger()


def setup_database():
    """
    Dynamically initialize, migrate, and upgrade the database.
    """
    with app.app_context():
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
    socketio.run(app=app, host=config.HOST, debug=config.DEBUG, log_output=logger)
