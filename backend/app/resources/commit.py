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
    expected_signature = "sha256=" + hmac.new(api_key.key.encode(), payload, hashlib.sha256).hexdigest()
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


"""
{'ref': 'refs/heads/other', 'before': '562e1a6728dca4e6a4134ad4e7d9b534914db8cf', 'after': 'fec4b5b97d18825dc3f71fc095db0406177accff', 'repository': {'id': 890882516, 'node_id': 'R_kgDONRnJ1A', 'name': 'master', 'full_name': 'iheb-ben/master', 'private': False, 'owner': {'name': 'iheb-ben', 'email': '48122635+iheb-ben@users.noreply.github.com', 'login': 'iheb-ben', 'id': 48122635, 'node_id': 'MDQ6VXNlcjQ4MTIyNjM1', 'avatar_url': 'https://avatars.githubusercontent.com/u/48122635?v=4', 'gravatar_id': '', 'url': 'https://api.github.com/users/iheb-ben', 'html_url': 'https://github.com/iheb-ben', 'followers_url': 'https://api.github.com/users/iheb-ben/followers', 'following_url': 'https://api.github.com/users/iheb-ben/following{/other_user}', 'gists_url': 'https://api.github.com/users/iheb-ben/gists{/gist_id}', 'starred_url': 'https://api.github.com/users/iheb-ben/starred{/owner}{/repo}', 'subscriptions_url': 'https://api.github.com/users/iheb-ben/subscriptions', 'organizations_url': 'https://api.github.com/users/iheb-ben/orgs', 'repos_url': 'https://api.github.com/users/iheb-ben/repos', 'events_url': 'https://api.github.com/users/iheb-ben/events{/privacy}', 'received_events_url': 'https://api.github.com/users/iheb-ben/received_events', 'type': 'User', 'user_view_type': 'public', 'site_admin': False}, 'html_url': 'https://github.com/iheb-ben/master', 'description': 'ERP Solution', 'fork': False, 'url': 'https://github.com/iheb-ben/master', 'forks_url': 'https://api.github.com/repos/iheb-ben/master/forks', 'keys_url': 'https://api.github.com/repos/iheb-ben/master/keys{/key_id}', 'collaborators_url': 'https://api.github.com/repos/iheb-ben/master/collaborators{/collaborator}', 'teams_url': 'https://api.github.com/repos/iheb-ben/master/teams', 'hooks_url': 'https://api.github.com/repos/iheb-ben/master/hooks', 'issue_events_url': 'https://api.github.com/repos/iheb-ben/master/issues/events{/number}', 'events_url': 'https://api.github.com/repos/iheb-ben/master/events', 'assignees_url': 'https://api.github.com/repos/iheb-ben/master/assignees{/user}', 'branches_url': 'https://api.github.com/repos/iheb-ben/master/branches{/branch}', 'tags_url': 'https://api.github.com/repos/iheb-ben/master/tags', 'blobs_url': 'https://api.github.com/repos/iheb-ben/master/git/blobs{/sha}', 'git_tags_url': 'https://api.github.com/repos/iheb-ben/master/git/tags{/sha}', 'git_refs_url': 'https://api.github.com/repos/iheb-ben/master/git/refs{/sha}', 'trees_url': 'https://api.github.com/repos/iheb-ben/master/git/trees{/sha}', 'statuses_url': 'https://api.github.com/repos/iheb-ben/master/statuses/{sha}', 'languages_url': 'https://api.github.com/repos/iheb-ben/master/languages', 'stargazers_url': 'https://api.github.com/repos/iheb-ben/master/stargazers', 'contributors_url': 'https://api.github.com/repos/iheb-ben/master/contributors', 'subscribers_url': 'https://api.github.com/repos/iheb-ben/master/subscribers', 'subscription_url': 'https://api.github.com/repos/iheb-ben/master/subscription', 'commits_url': 'https://api.github.com/repos/iheb-ben/master/commits{/sha}', 'git_commits_url': 'https://api.github.com/repos/iheb-ben/master/git/commits{/sha}', 'comments_url': 'https://api.github.com/repos/iheb-ben/master/comments{/number}', 'issue_comment_url': 'https://api.github.com/repos/iheb-ben/master/issues/comments{/number}', 'contents_url': 'https://api.github.com/repos/iheb-ben/master/contents/{+path}', 'compare_url': 'https://api.github.com/repos/iheb-ben/master/compare/{base}...{head}', 'merges_url': 'https://api.github.com/repos/iheb-ben/master/merges', 'archive_url': 'https://api.github.com/repos/iheb-ben/master/{archive_format}{/ref}', 'downloads_url': 'https://api.github.com/repos/iheb-ben/master/downloads', 'issues_url': 'https://api.github.com/repos/iheb-ben/master/issues{/number}', 'pulls_url': 'https://api.github.com/repos/iheb-ben/master/pulls{/number}', 'milestones_url': 'https://api.github.com/repos/iheb-ben/master/milestones{/number}', 'notifications_url': 'https://api.github.com/repos/iheb-ben/master/notifications{?since,all,participating}', 'labels_url': 'https://api.github.com/repos/iheb-ben/master/labels{/name}', 'releases_url': 'https://api.github.com/repos/iheb-ben/master/releases{/id}', 'deployments_url': 'https://api.github.com/repos/iheb-ben/master/deployments', 'created_at': 1732013479, 'updated_at': '2024-12-30T14:23:37Z', 'pushed_at': 1736715832, 'git_url': 'git://github.com/iheb-ben/master.git', 'ssh_url': 'git@github.com:iheb-ben/master.git', 'clone_url': 'https://github.com/iheb-ben/master.git', 'svn_url': 'https://github.com/iheb-ben/master', 'homepage': None, 'size': 259, 'stargazers_count': 0, 'watchers_count': 0, 'language': 'Python', 'has_issues': True, 'has_projects': True, 'has_downloads': True, 'has_wiki': True, 'has_pages': False, 'has_discussions': False, 'forks_count': 0, 'mirror_url': None, 'archived': False, 'disabled': False, 'open_issues_count': 0, 'license': {'key': 'gpl-3.0', 'name': 'GNU General Public License v3.0', 'spdx_id': 'GPL-3.0', 'url': 'https://api.github.com/licenses/gpl-3.0', 'node_id': 'MDc6TGljZW5zZTk='}, 'allow_forking': True, 'is_template': False, 'web_commit_signoff_required': False, 'topics': [], 'visibility': 'public', 'forks': 0, 'open_issues': 0, 'watchers': 0, 'default_branch': 'main', 'stargazers': 0, 'master_branch': 'main'}, 'pusher': {'name': 'iheb-ben', 'email': '48122635+iheb-ben@users.noreply.github.com'}, 'sender': {'login': 'iheb-ben', 'id': 48122635, 'node_id': 'MDQ6VXNlcjQ4MTIyNjM1', 'avatar_url': 'https://avatars.githubusercontent.com/u/48122635?v=4', 'gravatar_id': '', 'url': 'https://api.github.com/users/iheb-ben', 'html_url': 'https://github.com/iheb-ben', 'followers_url': 'https://api.github.com/users/iheb-ben/followers', 'following_url': 'https://api.github.com/users/iheb-ben/following{/other_user}', 'gists_url': 'https://api.github.com/users/iheb-ben/gists{/gist_id}', 'starred_url': 'https://api.github.com/users/iheb-ben/starred{/owner}{/repo}', 'subscriptions_url': 'https://api.github.com/users/iheb-ben/subscriptions', 'organizations_url': 'https://api.github.com/users/iheb-ben/orgs', 'repos_url': 'https://api.github.com/users/iheb-ben/repos', 'events_url': 'https://api.github.com/users/iheb-ben/events{/privacy}', 'received_events_url': 'https://api.github.com/users/iheb-ben/received_events', 'type': 'User', 'user_view_type': 'public', 'site_admin': False}, 'created': False, 'deleted': False, 'forced': False, 'base_ref': None, 'compare': 'https://github.com/iheb-ben/master/compare/562e1a6728dc...fec4b5b97d18', 'commits': [{'id': 'fec4b5b97d18825dc3f71fc095db0406177accff', 'tree_id': 'ac9bff177c937cda7191de49933174ef7d9587f9', 'distinct': True, 'message': 'Update', 'timestamp': '2025-01-12T22:03:49+01:00', 'url': 'https://github.com/iheb-ben/master/commit/fec4b5b97d18825dc3f71fc095db0406177accff', 'author': {'name': 'iheb-bennouri', 'email': 'iheb.bennouri@campion-tech.com', 'username': 'iheb-bennouri'}, 'committer': {'name': 'iheb-bennouri', 'email': 'iheb.bennouri@campion-tech.com', 'username': 'iheb-bennouri'}, 'added': [], 'removed': [], 'modified': ['backend/app/__init__.py']}], 'head_commit': {'id': 'fec4b5b97d18825dc3f71fc095db0406177accff', 'tree_id': 'ac9bff177c937cda7191de49933174ef7d9587f9', 'distinct': True, 'message': 'Update', 'timestamp': '2025-01-12T22:03:49+01:00', 'url': 'https://github.com/iheb-ben/master/commit/fec4b5b97d18825dc3f71fc095db0406177accff', 'author': {'name': 'iheb-bennouri', 'email': 'iheb.bennouri@campion-tech.com', 'username': 'iheb-bennouri'}, 'committer': {'name': 'iheb-bennouri', 'email': 'iheb.bennouri@campion-tech.com', 'username': 'iheb-bennouri'}, 'added': [], 'removed': [], 'modified': ['backend/app/__init__.py']}}
"""


# noinspection PyMethodMayBeStatic
@commit_ns.route('/webhook')
class WebHook(Resource):
    @github_webhook_wrapper
    def post(self):
        print(request.headers)
        print('sha256=ede143fa2df3a2e38a74b2c7ed4a655796498cad82c5c39af7088db0b2ad0e70')
        print(commit_ns.payload)
