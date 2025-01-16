from os import getenv
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = getenv('LOG_FILE', '')
GITHUB_TOKEN = getenv('GITHUB_TOKEN', '')
GITHUB_SECRET = getenv('GITHUB_SECRET', '')
TESTING = getenv('TESTING', '').strip().upper() in ('1', 'TRUE')
ENV = getenv('ENV', 'production')
HOST = getenv('HOST', '127.0.0.1')
PORT = int(getenv('PORT', '5000'))
SERVER_NAME = getenv('SERVER_NAME', f'{HOST}:{PORT}')
DEBUG = getenv('DEBUG', '').strip().upper() in ('1', 'TRUE')
JWT_SECRET_KEY = getenv('JWT_SECRET_KEY', 'supersecretkey')
JWT_ACCESS_TOKEN_EXPIRES = int(getenv('JWT_ACCESS_TOKEN_EXPIRES', str(60 * 60 * 24 * 7)))
SQLALCHEMY_DATABASE_URI = getenv('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@127.0.0.1:5432/master')
SQLALCHEMY_TRACK_MODIFICATIONS = getenv('SQLALCHEMY_TRACK_MODIFICATIONS', '1').strip().upper() in ('1', 'TRUE')
