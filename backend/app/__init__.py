import inspect
from types import SimpleNamespace
from flask import Flask
from flask_socketio import SocketIO
from flask_restx import Api
from flask_migrate import Migrate
from . import config
from . import connector
from . import tools
from . import logger

api_register = set()
migrate = Migrate()
app = Flask(__name__)
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
    # Register all namespaces
    from app import resources
    configuration = SimpleNamespace()
    for name, value in vars(config).items():
        if name.isupper() and not name.startswith('_') and not name.endswith('_'):
            setattr(configuration, name, value)
    app.config.from_object(configuration)
    connector.db.init_app(app)
    socketio.init_app(app)
    api.init_app(app)
    migrate.init_app(app)
    for namespace in api_register:
        api.add_namespace(namespace)
    socketio.on_namespace(resources.ws.WebSocket(namespace='/ws'))
    return app
