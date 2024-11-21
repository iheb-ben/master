from pathlib import Path
from shutil import rmtree
from master.config import arguments
from master.config.logging import get_logger
from master.tools.path import is_folder_empty
from git import Repo, GitCommandError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, List, Optional, Callable
import time
import os

_logger = get_logger(__name__)


class GitRepoManager:
    __slots__ = ('repos', 'last_commits')

    def __init__(self):
        self.repos: Dict[str, Repo] = {}
        self.last_commits: Dict[str, str] = {}  # Tracks the last pulled commit hash for each repo

    def clone(self, url: str, path: str) -> None:
        """Clone a repository to a specified path."""
        try:
            repo: Optional[Repo] = None
            repo_path = Path(path).joinpath('.git')
            if repo_path.exists():
                if not is_folder_empty(str(repo_path)):
                    repo = Repo(path)
                else:
                    rmtree(path)
            if not repo:
                repo = Repo.clone_from(url, path)
            self.repos[path] = repo
            self.last_commits[path] = repo.head.commit.hexsha  # Save initial commit hash
            _logger.info(f"Cloned repo from {url} to {path}")
        except GitCommandError as e:
            _logger.error(f"Error cloning repo: {e}")

    def switch_branch(self, repo_name: str, branch: str) -> None:
        """Switch to a specific branch in a repository."""
        repo = self.repos.get(repo_name)
        if repo is None:
            _logger.warning(f"Repository {repo_name} not found.")
            return
        try:
            repo.git.checkout(branch)
            _logger.info(f"Switched to branch '{branch}' in {repo_name}.")
        except GitCommandError as e:
            _logger.error(f"Error switching branch: {e}", exc_info=True)

    def pull(self, repo_name: str) -> None:
        """Pull latest changes and show commits since the last pull."""
        repo = self.repos.get(repo_name)
        if repo is None:
            _logger.warning(f"Repository {repo_name} not found.")
            return

        last_commit = self.last_commits.get(repo_name)
        try:
            repo.remotes.origin.pull()
            new_last_commit = repo.head.commit.hexsha

            if last_commit:
                _logger.info(f"Changes in {repo_name} since last commit {last_commit}:")
                for commit in repo.iter_commits(f'{last_commit}..{new_last_commit}'):
                    _logger.info(f"- {commit.hexsha[:7]}: {commit.message} by {commit.author.name}")

            # Update the last commit hash
            self.last_commits[repo_name] = new_last_commit
        except GitCommandError as e:
            _logger.error(f"Error pulling repo: {e}", exc_info=True)

    def commit_and_push(self, repo_name: str, message: str) -> None:
        """Stage all changes, commit, and push to the remote repository."""
        repo = self.repos.get(repo_name)
        if repo is None:
            _logger.warning(f"Repository {repo_name} not found.")
            return
        try:
            repo.git.add(A=True)  # Stage all changes
            repo.index.commit(message)
            repo.remotes.origin.push()
            _logger.info(f"Committed and pushed changes in {repo_name}: '{message}'")
        except GitCommandError as e:
            _logger.error(f"Error during commit and push: {e}", exc_info=True)

    def watch_changes(self, repo_name: str, func: Callable) -> None:
        """Monitor a repository for file changes and log them."""
        repo = self.repos.get(repo_name)
        if repo is None:
            _logger.warning(f"Repository {repo_name} not found.")
            return
        path = repo.working_tree_dir
        observer = Observer()

        class ChangeHandler(FileSystemEventHandler):
            def on_any_event(self, event):
                if not event.is_directory:
                    _logger.debug(f"Change detected in {repo_name}: {event.event_type} - {event.src_path}")
                    func(observer, repo_name)

        event_handler = ChangeHandler()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        _logger.info(f"Started watching for changes in {repo_name}.")

        try:
            while observer.is_alive():
                time.sleep(1)  # Keeps the observer alive
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def setup(self):
        for repo_details in arguments['git']:
            self.clone(**repo_details)
        for path in self.repos.keys():
            arguments['addons'].append(str(path))
