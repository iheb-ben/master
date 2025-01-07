from app import db
from app.models import BaseModel

user_access_right = db.Table(
    'user_access_right',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('access_right_id', db.Integer, db.ForeignKey('access_right.id'), primary_key=True)
)


class Partner(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(80), nullable=False)
    lastname = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(30), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('User', back_populates='partner')


class User(db.Model):
    # Enforce role selection
    __table_args__ = (
        db.CheckConstraint("role IN ('public', 'user')", name='check_user_role'),
    )

    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean, default=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(6), nullable=False, default='user')
    sessions = db.relationship(
        'Session',
        back_populates='user',
        cascade='all, delete-orphan'
    )
    partner = db.relationship(
        'Partner',
        back_populates='user',
        uselist=False,  # Ensures one-to-one relationship
        cascade='all, delete-orphan'
    )
    access_rights = db.relationship(
        'AccessRight',
        secondary=user_access_right,
        backref=db.backref('users', lazy='dynamic')
    )
    suspend_until = db.Column(db.DateTime(), nullable=True)
    # Account settings
    single_session_mode = db.Column(db.Boolean)


class AccessRightCategory(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    access_rights = db.relationship(
        'AccessRight',
        back_populates='category',
        cascade='all, delete-orphan'
    )


class AccessRight(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('access_right_category.id'), nullable=False)
    category = db.relationship('AccessRightCategory', back_populates='access_rights')
