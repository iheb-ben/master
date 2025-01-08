import functools
from flask import request, abort
from flask_restx import Namespace
from app.connector import db
from . import admin_setup


def login_required(namespace: Namespace):
    from app.resources import ResponseMessages

    def _wrapper(func):
        @namespace.doc(security='BearerAuth')
        @namespace.response(code=401, description=ResponseMessages.FORBIDDEN.value)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if request.user.role == 'public':
                abort(403, ResponseMessages.FORBIDDEN.value)
            return func(*args, **kwargs)
        return wrapper
    return _wrapper
