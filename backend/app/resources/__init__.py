from enum import Enum


class ResponseMessages(Enum):
    INVALID_CREDENTIALS = 'Invalid username or password'
    ACCOUNT_SUSPENDED = 'Account is suspended'
    LOGIN_ERROR = f'{INVALID_CREDENTIALS} | {ACCOUNT_SUSPENDED}'
    FORBIDDEN = 'Access is denied'
    SERVER_ERROR = 'Internal server error'


from . import auth
from . import user
from . import ws
