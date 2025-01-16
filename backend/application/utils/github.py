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


def get_all_commits(owner: str, repository: str, branch: str) -> List[Dict]:
    url = f'{BASE_URL}/repos/{owner}/{repository}/commits'
    response = get_url(url, headers=HEADERS, params={'sha': branch})
    if response.status_code != 200:
        raise Exception(f"Failed to fetch commits: {response.status_code}, {response.json()}")
    commits = response.json()
    return [{
        'message': commit['commit']['message'],
        'committer': commit['commit']['author'],
        'timestamp': commit['commit']['author']['date'],
    } for commit in commits]
