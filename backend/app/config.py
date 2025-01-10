import os
from dotenv import load_dotenv

load_dotenv()

TESTING = os.getenv('TESTING', '').strip().upper() in ('1', 'TRUE')
PORT = int(os.getenv('PORT', 5000))
SERVER_NAME = os.getenv('SERVER_NAME', f'127.0.0.1:{PORT}')
DEBUG = os.getenv('DEBUG', '').strip().upper() in ('1', 'TRUE')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'supersecretkey')
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 60 * 60 * 24 * 7))
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@127.0.0.1:5432/master')
SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'True').strip().upper() in ('1', 'TRUE')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'debug').upper()
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Update configuration values
PORT = int(SERVER_NAME.rsplit(':')[1])
HOST = SERVER_NAME.rsplit(':')[0]
os.environ['SERVER_NAME'] = SERVER_NAME
os.environ['PORT'] = str(PORT)
