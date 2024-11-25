from multiprocessing import Process
from pathlib import Path
from shutil import rmtree
from git import Repo, GitCommandError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, Optional
import time
import json
import os
import logging
import requests

from master.core import arguments, signature
from master.core.jwt import generate_jwt
from master.tools.paths import is_folder_empty

_logger = logging.getLogger(__name__)
token = generate_jwt(payload=signature, expiration_minutes=0)


class GitRepoManager:
    __slots__ = ('processes', 'repos', 'last_commits')

    def __init__(self):
        self.processes: Dict[str, Process] = {}
        self.repos: Dict[str, Repo] = {}
        self.last_commits: Dict[str, str] = {}

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
            self.last_commits[path] = repo.head.commit.hexsha
            _logger.info(f"Cloned repo from {url} to [{path}]")
        except GitCommandError as e:
            _logger.error(f"Error cloning repo: {e}")

    def switch_branch(self, repo_path: str, branch: str) -> None:
        """Switch to a specific branch in a repository."""
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
        repo = self.repos.get(repo_path)
        if repo is None:
            _logger.warning(f'Repository [{repo_path}] not found.')
            return
        last_commit = self.last_commits.get(repo_path)
        try:
            repo.remotes.origin.pull()
            new_last_commit = repo.head.commit.hexsha
            if last_commit:
                _logger.info(f"Changes in [{repo_path}] since last commit {last_commit}:")
                for commit in repo.iter_commits(f'{last_commit}..{new_last_commit}'):
                    requests.post(f'http://localhost:{arguments["port"]}/pipeline/repository/{hash(repo_path)}/commit/add?token={token}', json.dumps({
                        'hexsha': commit.hexsha,
                        'message': commit.message,
                        'author': commit.author.name,
                    }))
                    _logger.info(f"repo:[{repo_path}] - {commit.hexsha[:7]}: {commit.message} by {commit.author.name}")
            # Update the last commit hash
            self.last_commits[repo_path] = new_last_commit
        except GitCommandError as e:
            _logger.error(f"Error pulling repo: {e}", exc_info=True)

    def commit_and_push(self, repo_path: str, message: str) -> None:
        """Stage all changes, commit, and push to the remote repository."""
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

    def watch_changes(self, repo_path: str) -> None:
        """Start a watcher for a given repository in a separate process."""
        if repo_path in self.processes and self.processes[repo_path].is_alive():
            _logger.warning(f'Watcher already running for [{repo_path}].')
            return
        self.processes[repo_path] = process = Process(target=monitor_repo, args=(repo_path, token))
        process.start()
        _logger.info(f'Started watcher process for [{repo_path}] (PID: {process.pid}).')

    def stop_watchers(self) -> None:
        """Stop all running watcher processes."""
        for repo_path, process in self.processes.items():
            if process.is_alive():
                _logger.info(f"Stopping watcher process for [{repo_path}] (PID: {process.pid}).")
                process.terminate()
                process.join()
        self.processes.clear()


def monitor_repo(repo_path: str, system_token: str):
    """Monitor repository changes and handle file system events."""
    observer = Observer()

    class ChangeHandler(FileSystemEventHandler):
        def on_any_event(self, event):
            if not event.is_directory:
                _logger.info(f"[{repo_path}] Change detected: {event.event_type} - {event.src_path}")
                requests.get(f'http://localhost:{arguments["port"]}/pipeline/notify/{hash(repo_path)}?token={system_token}')

    event_handler = ChangeHandler()
    observer.schedule(event_handler, repo_path, recursive=True)
    observer.start()
    _logger.info(f"[{repo_path}] Watching changes.")
    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
    finally:
        observer.stop()
        _logger.info(f"[{repo_path}] Stopped watching changes.")
