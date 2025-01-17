import functools
from datetime import datetime
from functools import wraps
from os import makedirs
from pathlib import Path
from typing import Optional, List, Dict, Callable
from uuid import uuid1
from application import api, config
from application.connector import db, check_db_session
from application.models.user import Partner
from application.models.commit import Commit, Repository, Branch
from application.utils.github import get_all_branches, get_all_commits
from flask import request, abort, current_app
from flask_restx import Namespace, Resource
import hmac
import json
import hashlib


def verify_github_signature(payload, signature) -> bool:
    if not config.GITHUB_SECRET:
        return True
    expected_signature = f'sha256={hmac.new(config.GITHUB_SECRET.encode(), payload, hashlib.sha256).hexdigest()}'
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


def find_or_create_partner(email: str, name: str, username: str) -> Partner:
    partner: Optional[Partner] = Partner.query.filter_by(email=email).first()
    if not partner:
        partner = Partner(email=email, firstname=name, github_username=username)
        db.session.add(partner)
        db.session.commit()
    return partner


def log_json_error(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            json_file = Path(config.LOG_FOLDER) / f'webhook/payload_{uuid1()}.json'
            if not json_file.parent.is_dir():
                makedirs(json_file.parent, exist_ok=True)
            json.dump(open(json_file, 'w+'), commit_ns.payload)
            current_app.logger.error(f'[response in file: {json_file}], {e}', exc_info=True)
            raise e
    return wrapper


# noinspection PyMethodMayBeStatic
@commit_ns.route('/webhook')
class WebHook(Resource):
    @github_webhook_wrapper
    @log_json_error
    def post(self) -> None:
        owner: Optional[Partner] = Partner.query.filter_by(github_id=commit_ns.payload['repository']['owner']['id']).first()
        if not owner:
            owner = Partner(
                firstname=commit_ns.payload['repository']['owner']['name'],
                github_username=commit_ns.payload['repository']['owner']['login'],
                github_id=commit_ns.payload['repository']['owner']['id'],
                email=commit_ns.payload['repository']['owner']['email'],
            )
            db.session.add(owner)
            db.session.commit()
        branch_name: str = commit_ns.payload['ref'].split('/')[-1]
        repository: Optional[Repository] = Repository.query.filter_by(github_id=commit_ns.payload['repository']['id']).first()
        if not repository:
            repository = Repository(
                github_id=commit_ns.payload['repository']['id'],
                name=commit_ns.payload['repository']['name'],
                owner_id=owner.id,
            )
            db.session.add(repository)
            db.session.commit()
            if config.GITHUB_TOKEN:
                branches_names = get_all_branches(owner.github_username, repository.name)
                for endpoint_branch_name in branches_names:
                    if Branch.query.filter_by(name=endpoint_branch_name, repository_id=repository.id).first():
                        continue
                    db.session.add(Branch(
                        name=endpoint_branch_name,
                        repository_id=repository.id,
                    ))
                if check_db_session():
                    db.session.commit()
        branch: Optional[Branch] = Branch.query.filter_by(name=branch_name, repository_id=repository.id).first()
        if not branch:
            branch = Branch(
                name=branch_name,
                repository_id=repository.id,
            )
            db.session.add(branch)
            db.session.commit()
        partners = {}
        commits: List[Dict] = commit_ns.payload['commits']
        last_commit: Optional[Commit] = Commit.query.filter_by(branch_id=branch.id).order_by(db.desc(Commit.timestamp)).first()
        if config.GITHUB_TOKEN:
            parameters = {
                'owner': owner.github_username,
                'repository': repository.name,
                'branch': branch.name,
            }
            if not last_commit or last_commit.reference != commit_ns.payload['before']:
                commits = get_all_commits(**parameters)
        raise Exception('etest')
        # for commit in commits:
        #     if Commit.query.filter_by(reference=commit['id']).first():
        #         continue
        #     comitter_email = commit['committer']['email']
        #     committer = partners.get(comitter_email)
        #     if not committer:
        #         partners[comitter_email] = committer = find_or_create_partner(
        #             name=commit['committer']['name'],
        #             username=commit['committer']['username'],
        #             email=comitter_email,
        #         )
        #     db.session.add(Commit(
        #         reference=commit['id'],
        #         name=commit['message'],
        #         timestamp=datetime.fromisoformat(commit['timestamp']),
        #         partner_id=committer.id,
        #         branch_id=branch.id,
        #     ))
        #     db.session.commit()
