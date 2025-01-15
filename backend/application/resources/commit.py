import functools
from datetime import datetime
from typing import Optional
from application import api, config
from application.connector import db, rollback_commit
from application.models.user import Partner
from application.models.commit import Commit, Repository, Branch
from application.utils import log_error
from flask import request, abort
from flask_restx import Namespace, Resource
import hmac
import hashlib


def verify_github_signature(payload, signature):
    if not config.GITHUB_KEY:
        return True
    expected_signature = f'sha256={hmac.new(config.GITHUB_KEY.encode(), payload, hashlib.sha256).hexdigest()}'
    return hmac.compare_digest(expected_signature, signature)


def github_webhook_wrapper(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user_agent = request.headers.get('User-Agent', '')
        if not user_agent.startswith('GitHub-Hookshot/'):
            abort(403, description='Invalid User-Agent')
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not signature:
            abort(403, description='Missing signature')
        if not verify_github_signature(request.data, signature):
            abort(403, description='Invalid signature')
        event_type = request.headers.get('X-Github-Event', 'ping')
        if event_type == 'ping':
            return {'message': 'pong'}, 200
        func(*args, **kwargs)
        return {'message': 'Event processed'}, 200
    return wrapper


commit_ns: Namespace = api.namespace(name='Commits', path='/commits', description='Commit management operations')


def find_partner(email: str, name: str) -> Partner:
    partner: Optional[Partner] = Partner.query.filter_by(email=email).first()
    if not partner:
        partner = Partner(email=email, firstname=name)
        db.session.add(partner)
        return partner
    return partner


# noinspection PyMethodMayBeStatic
@commit_ns.route('/webhook')
class WebHook(Resource):
    @github_webhook_wrapper
    @rollback_commit
    @log_error
    def post(self):
        owner: Optional[Partner] = Partner.query.filter_by(github_id=commit_ns.payload['repository']['owner']['id']).first()
        if not owner:
            owner = Partner(
                firstname=commit_ns.payload['repository']['owner']['name'],
                email=commit_ns.payload['repository']['owner']['email'],
                github_id=commit_ns.payload['repository']['owner']['id'],
            )
            db.session.add(owner)
        branch_name: str = commit_ns.payload['ref'].split('/')[-1]
        repository: Optional[Repository] = Repository.query.filter_by(github_id=commit_ns.payload['repository']['id']).first()
        if not repository:
            repository = Repository(
                github_id=commit_ns.payload['repository']['id'],
                name=commit_ns.payload['repository']['name'],
                owner=owner,
            )
            branch = Branch(
                name=branch_name,
                repository=repository,
            )
            db.session.add(repository)
            db.session.add(branch)
        else:
            branch: Optional[Branch] = Branch.query.filter_by(repository_id=repository.id).first()
            if not branch:
                branch = Branch(
                    name=branch_name,
                    repository=repository,
                )
                db.session.add(branch)
        partners = {}
        for commit in commit_ns.payload['commits']:
            committer = partners.get(commit['committer']['email'])
            if not committer:
                committer = find_partner(commit['committer']['email'], commit['committer']['name'])
                partners[committer.email] = committer
            new_commit = Commit(
                reference=commit['id'],
                name=commit['message'],
                timestamp=datetime.fromisoformat(commit['timestamp']),
                partner=committer,
                branch=branch,
            )
            db.session.add(new_commit)
