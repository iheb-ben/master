from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_restx import Api
from flask_migrate import Migrate
from . import config
from . import tools
from . import logger

migrate = Migrate()
db = SQLAlchemy()
socketio = SocketIO()
api = Api(
    version='1.0',
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
    app = Flask(__name__)
    app.config.from_object(config.Config)
    db.init_app(app)
    socketio.init_app(app)
    api.init_app(app)
    migrate.init_app(app)
    # Register all namespaces
    from app import resources
    api.add_namespace(resources.auth.auth_ns, path='/auth')
    api.add_namespace(resources.user.user_ns, path='/users')
    socketio.on_namespace(resources.ws.WebSocket(namespace='/ws'))
    return app
