import functools
from flask import request, abort
from flask_restx import Namespace
from app.connector import db
from . import setup


def login_required(namespace: Namespace):
    from app.resources import ResponseMessages

    def _wrapper(func):
        @namespace.doc(security='BearerAuth')
        @namespace.response(code=401, description=ResponseMessages.FORBIDDEN.value)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for access in request.user.access_rights:
                if access.name == 'base.public':
                    abort(403, ResponseMessages.FORBIDDEN.value)
            return func(*args, **kwargs)
        return wrapper
    return _wrapper


def with_access(namespace: Namespace, access_rights=None):
    from app.resources import ResponseMessages
    access_rights = access_rights or []

    def _wrapper(func):
        @login_required(namespace)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not access_rights:
                return func(*args, **kwargs)
            for access in request.user.access_rights:
                if access.name in access_rights:
                    return func(*args, **kwargs)
            abort(403, ResponseMessages.FORBIDDEN.value)
        return wrapper
    return _wrapper
