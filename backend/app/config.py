import os
from dotenv import load_dotenv

load_dotenv()

TESTING = os.getenv('TESTING', '').strip().upper() in ('1', 'TRUE')
ENV = os.getenv('ENV', 'development')
MODE = os.getenv('MODE', 'master')
HOST = os.getenv('HOST', 'localhost')
PORT = int(os.getenv('PORT', 5000))
SERVER_NAME = f'{HOST}:{PORT}'
DEBUG = os.getenv('DEBUG', '').strip().upper() in ('1', 'TRUE')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'supersecretkey')
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 60 * 60 * 24 * 7))
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@127.0.0.1:5432/master')
SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'True').strip().upper() in ('1', 'TRUE')
# Update configuration values
os.environ['SERVER_NAME'] = SERVER_NAME
os.environ['PORT'] = str(PORT)
