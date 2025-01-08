import functools
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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
