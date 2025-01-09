import functools
from enum import Enum
from flask import request, abort


def validate_payload(namespace, fields):
    def _wrapper(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for field in set(fields):
                if not namespace.payload.get(field):
                    abort(400, ResponseMessages.REQUIRED_FIELDS.value % field)
            return func(*args, **kwargs)
        return wrapper
    return _wrapper


class ResponseMessages(Enum):
    INVALID_CREDENTIALS = 'Invalid username or password'
    ACCOUNT_SUSPENDED = 'Account is suspended'
    LOGIN_ERROR = f'{INVALID_CREDENTIALS} | {ACCOUNT_SUSPENDED}'
    FORBIDDEN = 'Access is denied'
    SERVER_ERROR = 'Internal server error'
    REQUIRED_FIELDS = 'Missing required field "%s"'


from . import auth
from . import user
from . import ws
