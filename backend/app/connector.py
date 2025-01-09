import functools
from typing import Callable
from flask_sqlalchemy import SQLAlchemy
from app import config

db = SQLAlchemy()


def check_db_session() -> bool:
    if config.TESTING:
        return False
    return db.session.dirty or db.session.new or db.session.deleted


def rollback_commit(func: Callable):
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
