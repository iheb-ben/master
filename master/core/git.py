import threading
from collections import OrderedDict
from functools import wraps
from urllib.parse import quote, urlencode
from pathlib import Path
from shutil import rmtree
from git import Repo, GitCommandError
from typing import Dict, Optional, Callable, List
import time
import json
import logging
import requests

from master.core import arguments, signature
from master.core.jwt import generate_jwt
from master.core.threads import worker
from master.tools.paths import is_folder_empty

_logger = logging.getLogger(__name__)
token = generate_jwt(payload=signature, expiration_minutes=0)
directory = Path(arguments['directory']).joinpath('repositories')
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
    query_params = urlencode({"token": token})
    return f'http://localhost:{arguments["port"]}/pipeline/repository/{project}/{branch}/{endpoint}?{query_params}'


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
            repo_path = Path(path).joinpath('.git')
            if repo_path.exists():
                if not is_folder_empty(repo_path, False):
                    repo = Repo(path)
                else:
                    rmtree(path)
            if not repo:
                repo = Repo.clone_from(url, path)
            self.repos[path] = repo
            self._repo_locks[path] = threading.RLock()
            self._last_commits[path] = repo.head.commit.hexsha
            _logger.info(f"Cloned repo from {url} to [{path}]")
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
            last_commit = self.last_commits.get(repo_path)
            try:
                repo.remotes.origin.pull()
                new_last_commit = repo.head.commit.hexsha
                if last_commit:
                    _logger.info(f'Changes in [{repo_path}] since last commit {last_commit}:')
                    for commit in repo.iter_commits(f'{last_commit}..{new_last_commit}'):
                        requests.post(_url(repo_path, 'commit/add'), json.dumps({
                            'hexsha': commit.hexsha,
                            'message': commit.message,
                            'author': commit.author.name,
                        }))
                        _logger.info(f'repo:[{repo_path}] - {commit.hexsha[:7]}:"{commit.message}" by "{commit.author.name}".')
                self._last_commits[repo_path] = new_last_commit
                if not last_commit or last_commit != new_last_commit:
                    requests.get(_url(repo_path, 'build'))
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


def configure(manager: GitRepoManager):
    for git_details in arguments['git']:
        pass
