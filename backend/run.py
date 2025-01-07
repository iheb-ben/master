import datetime
import functools
from typing import Optional
from flask import request
from app import create_app, db, socketio
from app.config import Config
from app.logger import setup_logger
from app.models.session import Session
from app.models.user import User
from app.tools import client_public_ip
from app.utils import check_db_session
from app.utils.admin_setup import ensure_admin_user, PUBLIC_USER_ID

app = create_app()
logger = setup_logger()


def _before_request(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> None:
        if not hasattr(request, 'user'):
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
    token = request.authorization and request.authorization.token or ''
    ip_address = client_public_ip()
    if ip_address:
        if not token.startswith('Bearer '):
            return logger.debug(f'No attached token was found for IP {ip_address}')
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


if __name__ == '__main__':
    with app.app_context():
        # db.drop_all()
        db.create_all()
        ensure_admin_user()
        if check_db_session():
            db.session.commit()
    socketio.run(app=app, host='127.0.0.1', port=Config.PORT, debug=Config.DEBUG, log_output=logger)
