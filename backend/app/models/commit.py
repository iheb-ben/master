from app.connector import db
from app.models import BaseModel


class Commit(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(255), unique=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id', ondelete='CASCADE'), nullable=False)
    partner = db.relationship('Partner', back_populates='commits')

