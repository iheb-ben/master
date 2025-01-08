import inspect
from types import SimpleNamespace
from flask import Flask
from flask_restx import Api
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_cors import CORS
from . import config
from . import connector
from . import tools
from . import logger

migrate = Migrate()
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})
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
    app.config.from_object(configuration)
    connector.db.init_app(app)
    socketio.init_app(app)
    api.init_app(app)
    migrate.init_app(app)
    # Register all namespaces
    from app import resources
    return app
