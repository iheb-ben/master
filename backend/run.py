import datetime
import functools
import os
from typing import Optional
from flask import request
from flask_migrate import init, migrate, upgrade
from app import create_app, socketio
from app import config, api, cors
from app.connector import db, check_db_session
from app.logger import setup_logger
from app.models.session import Session
from app.models.user import User
from app.tools import client_public_ip
from app.utils.setup import initialize_database, PUBLIC_USER_ID

app = create_app()
cors.init_app(app, resources={r"/*": {"origins": "http://localhost:3000"}})
logger = setup_logger()


def _before_request(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> None:
        if not hasattr(request, 'user') and request.path.startswith(api.prefix or '/'):
            user: Optional[User] = func(*args, **kwargs)
            if not user:
                user = User.query.filter_by(id=PUBLIC_USER_ID).first()
            request.user = user
            assert request.user, 'Major error, User not set in request'
    return wrapper


@app.before_request
@_before_request
def select_user() -> Optional[User]:
    current_datetime = datetime.datetime.utcnow()
    token: str = request.authorization and request.authorization.token or ''
    ip_address = client_public_ip()
    if ip_address and token.startswith('Bearer '):
        session: Optional[Session] = Session.query.filter_by(token=token.split(' ')[-1], ip_address=ip_address).first()
        if not session:
            return logger.debug(f'No session was found for IP {ip_address}')
        if not session.active:
            return logger.debug(f'User {session.user.id} session is not active')
        if session.expires_at <= current_datetime:
            return logger.debug(f'User {session.user.id} token is expired')
        if not session.user.active:
            return logger.debug(f'User {session.user.id} is not active')
        if session.user.suspend_until and session.user.suspend_until > current_datetime:
            return logger.debug(f'User {session.user.id} is suspended')
        return session.user


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
