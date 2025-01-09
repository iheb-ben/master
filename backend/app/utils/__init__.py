import datetime
import functools
from typing import List, Callable
from flask import request, abort
from flask_restx import Namespace, Model
from . import setup


def validate_payload(namespace: Namespace, model: Model):
    from app.resources import ResponseMessages

    def _wrapper(func: Callable):
        @namespace.response(code=400, description=ResponseMessages.REQUIRED_FIELDS.value % 'FIELD_NAME')
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for field in model.keys():
                if not namespace.payload.get(field) and model[field].required:
                    abort(400, ResponseMessages.REQUIRED_FIELDS.value % field)
            return func(*args, **kwargs)
        return wrapper
    return _wrapper


def login_required(namespace: Namespace):
    from app.resources import ResponseMessages

    def _wrapper(func: Callable):
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

    def _wrapper(func: Callable):
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
