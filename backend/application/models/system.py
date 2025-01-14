from application.connector import db
from application.models import BaseModel


class ApiKey(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean, default=True)
    key = db.Column(db.String(255), nullable=False, unique=True)
    domain = db.Column(db.String(255), nullable=True, unique=True)
    expires_at = db.Column(db.DateTime, nullable=True)


class Parameter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    value = db.Column(db.String(255), nullable=False)
