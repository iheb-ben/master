from datetime import datetime, timezone
from application import config
from typing import List, Dict
from requests import HTTPError, get as get_url

BASE_URL = 'https://api.github.com'
HEADERS = {
    'Authorization': f'Bearer {config.GITHUB_TOKEN}',
    'Accept': 'application/vnd.github+json',
}


def get_all_branches(owner: str, repository: str) -> List[str]:
    url = f'{BASE_URL}/repos/{owner}/{repository}/branches'
    response = get_url(url, headers=HEADERS)
    if response.status_code != 200:
        raise HTTPError(f'Failed to fetch branches: {response.status_code}, {response.json()}')
    branches = response.json()
    return [branch['name'] for branch in branches]


def build_commit_response(commit: Dict):
    timestamp = datetime.strptime(commit['commit']['author']['date'], '%Y-%m-%dT%H:%M:%SZ')
    return {
        'id': commit['sha'],
        'message': commit['commit']['message'],
        'committer': {
            'name': commit['commit']['committer']['name'],
            'email': commit['commit']['committer']['email'],
            'username': commit['committer']['login'],
        },
        'timestamp': timestamp.replace(tzinfo=timezone.utc).isoformat(),
    }


def get_all_commits(owner: str, repository: str, branch: str) -> List[Dict]:
    url = f'{BASE_URL}/repos/{owner}/{repository}/commits'
    response = get_url(url, headers=HEADERS, params={'sha': branch})
    if response.status_code != 200:
        raise HTTPError(f"Failed to fetch commits: {response.status_code}, {response.json()}")
    return [build_commit_response(commit) for commit in response.json()]


def get_commits(owner: str, repository: str, branch: str, from_commit: str, to_commit: str) -> List[Dict]:
    url = f'{BASE_URL}/repos/{owner}/{repository}/commits/{sha_from}..{sha_to}'
    response = get_url(url, headers=HEADERS, params={
        'sha': branch,
        'since': from_commit,
        'until': to_commit,
    })
    if response.status_code != 200:
        raise HTTPError(f"Failed to fetch commits: {response.status_code}, {response.json()}")
    return [build_commit_response(commit) for commit in response.json()]
