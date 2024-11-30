import threading
from collections import OrderedDict
from functools import wraps
from urllib.parse import quote, urlencode
from pathlib import Path
from shutil import rmtree
from typing import Dict, Optional, Callable, List
import time
import json
import logging

for logger_name in ['urllib3.connectionpool', 'git', 'git.cmd', 'git.repo.base']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL)

import requests
from git import Repo, GitCommandError

from master.core import arguments, signature
from master.core.jwt import generate_jwt
from master.core.threads import worker
from master.tools.norms import clean_string_advanced
from master.tools.paths import is_folder_empty

_logger = logging.getLogger(__name__)
token = generate_jwt(payload=signature, expiration_minutes=0)
directory = Path(arguments['directory']) / 'repositories'
if not directory.exists():
    directory.mkdir()


def _check_lock(func: Callable):
    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        if not hasattr(self, '_lock'):
            raise AttributeError('Instance must have "_lock" attribute for thread safety.')
        with getattr(self, '_lock'):
            return func(self, *args, **kwargs)
    return _wrapper


def _url(path: str, endpoint: str):
    repo_path = Path(path)
    project: str = quote(repo_path.parent.name)
    branch: str = quote(repo_path.name)
    if endpoint.startswith('/'):
        endpoint = endpoint[1:]
    if endpoint.endswith('/'):
        endpoint = endpoint[:-1]
    query_params = urlencode({'token': token})
    return f'http://localhost:{arguments["port"]}/pipeline/repository/{project}/{branch}/{endpoint}?{query_params}'


def _post_url(url, body) -> None:
    try:
        response = requests.post(url=url, json=body)
        response.raise_for_status()
    except requests.RequestException:
        pass


def _get_url(url) -> None:
    try:
        response = requests.get(url=url)
        response.raise_for_status()
    except requests.RequestException:
        pass


# noinspection PyArgumentList
class GitRepoManager:
    __slots__ = ('repos', '_lock', '_repo_locks', '_last_commits')

    def __init__(self):
        self.repos: Dict[str, Repo] = OrderedDict()
        self._repo_locks = {}  # Lock for each repo
        self._lock = threading.RLock()  # Global lock
        self._last_commits: Dict[str, str] = {}

    @_check_lock
    def clone(self, url: str, path: str) -> None:
        """Clone a repository to a specified path."""
        try:
            repo: Optional[Repo] = None
            repo_path = Path(path) / '.git'
            if repo_path.exists():
                if not is_folder_empty(repo_path, False):
                    repo = Repo(path)
                else:
                    rmtree(path)
            if not repo:
                repo = Repo.clone_from(url, path)
                _logger.debug(f"Cloned repo from {url} to [{path}]")
            self.repos[path] = repo
            self._repo_locks[path] = threading.RLock()
            self._last_commits[path] = repo.head.commit.hexsha
        except GitCommandError as e:
            _logger.error(f"Error cloning repo: {e}")

    @_check_lock
    def _check_repo_lock(self, repo_path: str):
        return self._repo_locks.get(repo_path)

    def switch_branch(self, repo_path: str, branch: str) -> None:
        """Switch to a specific branch in a repository."""
        with self._check_repo_lock(repo_path):
            repo = self.repos.get(repo_path)
            if repo is None:
                _logger.warning(f"Repository [{repo_path}] not found.")
                return
            try:
                repo.git.checkout(branch)
                _logger.info(f'Switched to branch "{branch}" in [{repo_path}].')
            except GitCommandError as e:
                _logger.error(f"Error switching branch: {e}", exc_info=True)

    def pull(self, repo_path: str) -> None:
        """Pull latest changes and show commits since the last pull."""
        with self._check_repo_lock(repo_path):
            repo = self.repos.get(repo_path)
            if repo is None:
                _logger.warning(f'Repository [{repo_path}] not found.')
                return
            last_commit = self._last_commits.get(repo_path)
            try:
                repo.remotes.origin.pull()
                new_last_commit = repo.head.commit.hexsha
                if last_commit != new_last_commit:
                    _logger.debug(f'Changes in [{repo_path}] since last commit {last_commit}:')
                    for commit in repo.iter_commits(f'{last_commit}..{new_last_commit}'):
                        _post_url(url=_url(repo_path, 'commit/add'), body={
                            'hexsha': commit.hexsha,
                            'message': commit.message,
                            'author': {
                                'name': commit.author.name,
                                'email': commit.author.email,
                            },
                        })
                        _logger.info(f'repo:[{repo_path}] - {commit.hexsha[:7]}:"{clean_string_advanced(commit.message)}" by "{commit.author.name}".')
                    self._last_commits[repo_path] = new_last_commit
                    _get_url(url=_url(repo_path, 'build'))
            except GitCommandError as e:
                _logger.error(f"Error pulling repo: {e}", exc_info=True)

    def commit_and_push(self, repo_path: str, message: str) -> None:
        """Stage all changes, commit, and push to the remote repository."""
        with self._check_repo_lock(repo_path):
            repo = self.repos.get(repo_path)
            if repo is None:
                _logger.warning(f"Repository [{repo_path}] not found.")
                return
            try:
                repo.git.add(A=True)
                repo.index.commit(message)
                repo.remotes.origin.push()
                _logger.info(f'Committed and pushed changes in [{repo_path}]: "{message}".')
            except GitCommandError as e:
                _logger.error(f"Error during commit and push: {e}", exc_info=True)

    @_check_lock
    def delete(self, repo_path: str) -> None:
        """Remove repo from manager."""
        if repo_path not in self.repos:
            _logger.warning(f'Repository [{repo_path}] not found.')
            return
        with self._check_repo_lock(repo_path):
            if not Path(repo_path).exists():
                return
            del self.repos[repo_path]
            del self._repo_locks[repo_path]
            del self._last_commits[repo_path]
            rmtree(repo_path)

    @_check_lock
    def _paths(self) -> List[str]:
        return [path for path in self.repos.keys()]

    def check(self) -> None:
        for repo_path in self._paths():
            self.pull(repo_path)

    @worker
    def run(self) -> None:
        if not arguments['pipeline_webhook']:
            self.check()
        time.sleep(arguments['pipeline_interval'])

    def configure(self) -> None:
        """Configure repositories based on the provided arguments."""
        added_sets = set()
        build_message: Callable = lambda p, d: f'Missing "{p}" in configuration details: {json.dumps(d)}. Skipping.'
        for details in arguments['git']:
            string = json.dumps(details)
            if string in added_sets:
                continue
            added_sets.add(string)
            owner = details.get('owner')
            repo = details.get('repo')
            # Check for missing essential keys
            if not repo:
                _logger.warning(build_message('repo', details))
                continue
            if not owner:
                _logger.warning(build_message('owner', details))
                continue
            branch = details.get('branch', 'main')
            repo_token = details.get('token', '')
            token_prefix = repo_token and f'{repo_token}@' or ''
            url = f'https://{token_prefix}github.com/{owner}/{repo}.git'
            repo_path = str(directory / repo / branch)
            # Clone the repository and/or add it to manager if already exists
            arguments['addons_paths'].append(repo_path)
            self.clone(url=url, path=repo_path)
