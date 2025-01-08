from flask import request
from datetime import datetime
from app.connector import db
from app.tools import current_user_id


class BaseModel(db.Model):
    __abstract__ = True

    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    write_date = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    create_uid = db.Column(db.Integer, nullable=False)
    write_uid = db.Column(db.Integer, nullable=True)

    # Event listeners for audit field management
    def __init_subclass__(cls):
        @db.event.listens_for(cls, 'before_insert')
        def set_create_metadata(mapper, connection, target):
            target.create_date = datetime.utcnow()
            target.create_uid = current_user_id()

        @db.event.listens_for(cls, 'before_update')
        def set_write_metadata(mapper, connection, target):
            target.write_date = datetime.utcnow()
            target.write_uid = current_user_id()


from . import user
from . import session
