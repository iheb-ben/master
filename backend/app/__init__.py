import functools
import inspect
from datetime import datetime
from types import SimpleNamespace
from typing import Optional
from flask import Flask, request
from flask_restx import Api
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_cors import CORS
from . import models
from . import config
from . import connector
from . import tools
from . import logger
from . import utils

migrate = Migrate()
cors = CORS()
socketio = SocketIO()
api = Api(
    version='1.0',
    prefix='/api',
    title='Backend API',
    description='Swagger UI for the ERP API',
    contact_email='bennouri.iheb@gmail.com',
    authorizations={
        'BearerAuth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Provide a valid Bearer token in the format: Bearer <token>',
        },
    },
)


def create_app():
    configuration = SimpleNamespace()
    for name, value in vars(config).items():
        if name.isupper() and not name.startswith('_') and not name.endswith('_'):
            setattr(configuration, name, value)
    globals()['app'] = Flask(__name__)
    app.config.from_object(configuration)
    api.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": "http://127.0.0.1:3000"}})
    connector.db.init_app(app)
    migrate.init_app(app, connector.db)
    socketio.init_app(app)
    # Register all namespaces
    from app import resources
    app.before_request(_read_user)
    return app


def _before_request(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> None:
        if not hasattr(request, 'user') and request.path.startswith(api.prefix or '/'):
            user: Optional[models.user.User] = func(*args, **kwargs)
            if not user:
                user = models.user.User.query.filter_by(id=utils.setup.PUBLIC_USER_ID).first()
            request.user = user
            assert request.user, 'Major error, User not set in request'
    return wrapper


@_before_request
def _read_user() -> Optional[models.user.User]:
    current_datetime = datetime.utcnow()
    token: str = request.authorization and request.authorization.token or ''
    ip_address = tools.client_public_ip()
    if ip_address and token.startswith('Bearer '):
        session: Optional[models.session.Session] = models.session.Session.query.filter_by(token=token.split(' ')[-1], ip_address=ip_address).first()
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
