import threading
from collections import OrderedDict
from urllib.parse import quote, urlencode
from pathlib import Path
from shutil import rmtree
from typing import Dict, Optional, Callable, List, Any
import time
import json
import logging

for logger_name in ['urllib3.connectionpool', 'git', 'git.cmd', 'git.repo.base']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL)

import requests
from git import Repo, GitCommandError, InvalidGitRepositoryError

from master.api import check_lock
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


def _url(path: str, endpoint: str):
    repo_path = Path(path)
    project: str = quote(repo_path.parent.name)
    branch: str = quote(repo_path.name)
    if endpoint.startswith('/'):
        endpoint = endpoint[1:]
    if endpoint.endswith('/'):
        endpoint = endpoint[:-1]
    return f'http://localhost:{arguments["port"]}/pipeline/git/repository/{project}/{branch}/{endpoint}'


# noinspection PyArgumentList
class GitRepoManager:
    __slots__ = ('repos', '_lock', '_repo_locks')

    def __init__(self):
        self.repos: Dict[str, Repo] = OrderedDict()
        self._repo_locks = {}  # Lock for each repo
        self._lock = threading.RLock()  # Global lock

    @staticmethod
    def submit_commit(repo_path: str, body: Dict[str, Any]) -> bool:
        try:
            response = requests.post(url=_url(repo_path, 'commit/add'), json=body, headers={'Authorization': f'Bearer {token}'})
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            _logger.error(f'Server error: {str(e)}')
            return False

    @staticmethod
    def trigger_build(repo_path: str) -> bool:
        try:
            response = requests.get(url=_url(repo_path, 'build'), headers={'Authorization': f'Bearer {token}'})
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            _logger.error(f'Server error: {str(e)}')
            return False

    @check_lock
    def clone(self, url: str, path: str) -> None:
        """Clone a repository to a specified path."""
        repo: Optional[Repo] = None
        repo_path = Path(path) / '.git'
        try:
            if repo_path.is_dir():
                if not is_folder_empty(repo_path, False):
                    repo = Repo(repo_path.parent)
                else:
                    rmtree(repo_path.parent)
        except InvalidGitRepositoryError:
            rmtree(repo_path.parent)
        try:
            if not repo:
                repo = Repo.clone_from(url, repo_path.parent)
                _logger.debug(f"Cloned repo from {url} to [{path}]")
            self.repos[path] = repo
            self._repo_locks[path] = threading.RLock()
        except GitCommandError as e:
            _logger.error(f"Error cloning repo: {e}")

    @check_lock
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
            last_commit = repo.head.commit.hexsha
            try:
                repo.remotes.origin.pull()
                new_last_commit = repo.head.commit.hexsha
            except GitCommandError as e:
                _logger.error(f"Error pulling repo: {e}", exc_info=True)
                new_last_commit = None
            if not new_last_commit:
                return
            if last_commit != new_last_commit:
                _logger.debug(f'Changes in [{repo_path}] since last commit {last_commit}:')
                for commit in repo.iter_commits(f'{last_commit}..{new_last_commit}'):
                    body = {
                        'hexsha': commit.hexsha,
                        'message': commit.message,
                        'author': {
                            'name': commit.author.name,
                            'email': commit.author.email,
                        },
                    }
                    if not self.submit_commit(repo_path, body):
                        repo.git.reset('--hard', last_commit)
                        return
                    _logger.info(f'repo:[{repo_path}] - {commit.hexsha[:7]}:"{clean_string_advanced(commit.message)}" by "{commit.author.name}".')
                if not self.trigger_build(repo_path):
                    repo.git.reset('--hard', last_commit)

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

    @check_lock
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
            rmtree(repo_path)

    @check_lock
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
            self.clone(url=url, path=repo_path)
