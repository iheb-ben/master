import functools
from flask import request, abort
from flask_restx import Namespace
from app import db
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


def check_db_session() -> bool:
    return db.session.dirty or db.session.new or db.session.deleted


def rollback_commit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # Commit if no exception occurs
            if check_db_session():
                db.session.commit()
            return result
        except Exception:
            if db.session.is_active:
                db.session.rollback()
            raise
    return wrapper
