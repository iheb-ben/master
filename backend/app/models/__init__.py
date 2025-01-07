from flask import request
from app import db
from datetime import datetime


class BaseModel(db.Model):
    __abstract__ = True

    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    write_date = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    create_uid = db.Column(db.Integer, nullable=False)
    write_uid = db.Column(db.Integer, nullable=True)


from . import user
from . import session


# Event listeners for audit field management
@db.event.listens_for(BaseModel, 'before_insert')
def set_create_metadata(mapper, connection, target):
    target.create_date = datetime.utcnow()
    target.create_uid = request.user.id


@db.event.listens_for(BaseModel, 'before_update')
def set_write_metadata(mapper, connection, target):
    target.write_date = datetime.utcnow()
    target.write_uid = request.user.id
