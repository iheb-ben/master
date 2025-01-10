import inspect
import os
from datetime import datetime
from functools import wraps
from types import SimpleNamespace
from typing import Optional, Callable
from flask import Flask, request, current_app
from flask_restx import Api
from flask_socketio import SocketIO
from flask_migrate import init, migrate as migrate_db, upgrade, Migrate
from flask_cors import CORS
from . import utils
from . import config
from . import tools
from . import logger as logger_config
from . import connector
from . import models

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
    server = Flask(__name__)
    server.config.from_object(configuration)
    api.init_app(server)
    cors.init_app(server, resources={r"/*": {"origins": "http://127.0.0.1:3000"}})
    connector.db.init_app(server)
    migrate.init_app(server, connector.db)
    socketio.init_app(server)
    # Register all namespaces
    from app import resources
    server.before_request(_read_user)
    return server


def setup_database(server: Flask):
    with server.app_context():
        # Initialize migrations directory if not present
        migrations_path = os.path.join(os.getcwd(), 'migrations')
        if not os.path.exists(migrations_path):
            init()
        # Generate migration script if needed
        migrate_db(message='Auto-generated migration')
        # Apply migrations
        upgrade()
        utils.setup.initialize_database()
        if connector.check_db_session():
            connector.db.session.commit()


def _before_request(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs) -> None:
        if not hasattr(request, 'user') and request.path.startswith(api.prefix):
            user: Optional[models.user.User] = func(*args, **kwargs)
            if not user:
                user = models.user.User.query.filter_by(id=utils.setup.PUBLIC_USER_ID).first()
            request.user = user
            assert request.user
    return wrapper


@_before_request
def _read_user() -> Optional[models.user.User]:
    current_datetime = datetime.utcnow()
    token: str = request.authorization and request.authorization.token or ''
    ip_address = tools.client_public_ip()
    if ip_address and token.startswith('Bearer '):
        session: Optional[models.session.Session] = models.session.Session.query.filter_by(
            token=token.split(' ')[-1],
            ip_address=ip_address,
        ).first()
        if not session:
            return current_app.logger.debug(f'No session was found for IP {ip_address}')
        if not session.active:
            return current_app.logger.debug(f'User {session.user.id} session is not active')
        if session.expires_at <= current_datetime:
            return current_app.logger.debug(f'User {session.user.id} token is expired')
        if not session.user.active:
            return current_app.logger.debug(f'User {session.user.id} is not active')
        if session.user.suspend_until and session.user.suspend_until > current_datetime:
            return current_app.logger.debug(f'User {session.user.id} is suspended')
        return session.user
