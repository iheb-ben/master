from application.connector import db


class Repository(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    github_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('partner.id', ondelete='CASCADE'), nullable=False)
    branches = db.relationship('Branch', back_populates='repository', cascade='all, delete-orphan')


class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    head_commit_id = db.Column(db.String(255), nullable=True)
    repository_id = db.Column(db.Integer, db.ForeignKey('repository.id', ondelete='CASCADE'), nullable=False)
    repository = db.relationship('Repository', back_populates='branches')
    commits = db.relationship('Commit', back_populates='branch', cascade='all, delete-orphan')


class Commit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id', ondelete='CASCADE'), nullable=False)
    partner = db.relationship('Partner', back_populates='commits')
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id', ondelete='CASCADE'), nullable=False)
    branch = db.relationship('Branch', back_populates='commits')
