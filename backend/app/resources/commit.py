import functools
from datetime import datetime
from app import api
from flask import request, abort
from flask_restx import Namespace, Resource
from app.models.system import ApiKey
import hmac
import hashlib


def verify_github_signature(payload, signature):
    api_key = ApiKey.query.filter_by(active=True, domain=None).first()
    if not api_key:
        api_key = ApiKey.query.filter_by(active=True, domain='GITHUB').first()
    if not api_key or (api_key.expires_at and api_key.expires_at < datetime.utcnow()):
        return False
    expected_signature = f'sha256={hmac.new(api_key.key.encode(), payload, hashlib.sha256).hexdigest()}'
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


# noinspection PyMethodMayBeStatic
@commit_ns.route('/webhook')
class WebHook(Resource):
    @github_webhook_wrapper
    def post(self):
        branch_name: str = commit_ns.payload['ref'].split('/')[-1]
        repository_ref: int = commit_ns.payload['repository']['id']
        repository_name: str = commit_ns.payload['repository']['name']
        repository_fullname: str = commit_ns.payload['repository']['full_name']
        owner_name: str = commit_ns.payload['repository']['owner']['name']
