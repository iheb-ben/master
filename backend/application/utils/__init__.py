import datetime
from enum import Enum
from functools import wraps
from typing import List, Callable, Iterable
from flask import request, abort, current_app
from flask_restx import Namespace, Model
from . import setup


class ResponseMessages(Enum):
    INVALID_CREDENTIALS = 'Invalid username or password'
    ACCOUNT_SUSPENDED = 'Account is suspended'
    LOGIN_ERROR = f'{INVALID_CREDENTIALS} | {ACCOUNT_SUSPENDED}'
    FORBIDDEN = 'Access is denied'
    SERVER_ERROR = 'Internal server error'
    REQUIRED_FIELDS = 'Missing required field "%s"'


def validate_payload(namespace: Namespace, model: Model):
    def _wrapper(func: Callable):
        @namespace.response(code=400, description=ResponseMessages.REQUIRED_FIELDS.value % 'FIELD_NAME')
        @wraps(func)
        def wrapper(*args, **kwargs):
            for field in model.keys():
                if not namespace.payload.get(field) and model[field].required:
                    abort(400, ResponseMessages.REQUIRED_FIELDS.value % field)
            return func(*args, **kwargs)
        return wrapper
    return _wrapper


def login_required(namespace: Namespace):
    def _wrapper(func: Callable):
        @namespace.doc(security='BearerAuth')
        @namespace.response(code=401, description=ResponseMessages.FORBIDDEN.value)
        @wraps(func)
        def wrapper(*args, **kwargs):
            for access in request.user.access_rights:
                if access.name == 'base.public':
                    abort(403, ResponseMessages.FORBIDDEN.value)
            return func(*args, **kwargs)
        return wrapper
    return _wrapper


def with_access(namespace: Namespace, access_rights=None):
    access_rights = access_rights or []
    assert isinstance(access_rights, Iterable)

    def _wrapper(func: Callable):
        @login_required(namespace)
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not access_rights:
                return func(*args, **kwargs)
            for access in request.user.access_rights:
                if access.name in access_rights:
                    return func(*args, **kwargs)
            abort(403, ResponseMessages.FORBIDDEN.value)
        return wrapper
    return _wrapper


def log_error(func: Callable):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(e, exc_info=True)
            raise e
    return wrapper
