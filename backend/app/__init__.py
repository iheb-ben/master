import inspect
import logging
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
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from . import config
from . import utils
from . import convertors
from . import tools
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
    server = Flask(import_name=__name__)
    server.config.from_object(configuration)
    api.init_app(server)
    cors.init_app(server, resources={r'/*': {'origins': 'http://127.0.0.1:3000'}})
    connector.db.init_app(server)
    migrate.init_app(server, connector.db)
    socketio.init_app(server)
    from app import resources
    server.url_map.converters['list'] = convertors.ListConverter
    server.url_map.converters['datetime'] = convertors.DateTimeConverter
    server.before_request(_before_request)
    server.after_request(_after_request)
    return server


def ensure_database_exists(server: Flask):
    db_uri = server.config['SQLALCHEMY_DATABASE_URI']
    engine = create_engine(db_uri)
    if not database_exists(engine.url):
        create_database(engine.url)


def setup_database(server: Flask):
    ensure_database_exists(server)
    with server.app_context():
        migrations_path = os.path.join(os.getcwd(), 'migrations')
        if not os.path.exists(migrations_path):
            init(template='flask')
        migrate_db(message='Auto-generated migration')
        upgrade()
        utils.setup.initialize_database()
        if connector.check_db_session():
            connector.db.session.commit()


def _before_request():
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

    if not hasattr(request, 'user') and request.path.startswith(api.prefix):
        user: Optional[models.user.User] = _read_user()
        if not user:
            user = models.user.User.query.filter_by(id=utils.setup.PUBLIC_USER_ID).first()
        request.user = user
        assert request.user


def _after_request(response):
    path = request.path
    method = request.method
    status_code = response.status
    content_length = response.headers.get('Content-Length', '0')
    current_app.logger.info(f"Method: {method}, Path: {path}, Status: {status_code}, Response Size: {content_length} bytes")
    return response
