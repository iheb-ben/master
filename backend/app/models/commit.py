from app.connector import db
from app.models import BaseModel


class Commit(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
