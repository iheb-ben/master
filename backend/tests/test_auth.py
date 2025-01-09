from tests import client
from app.config import SERVER_NAME

login_url = f'http://{SERVER_NAME}/api/auth/login'


def test_auth_required_fields(client):
    """Test login with missing data."""
    response = client.post(login_url, json={'username': 'admin'})
    assert response.status_code == 400


def test_auth_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(login_url, json={'username': '.', 'password': '.'})
    assert response.status_code == 401


def test_auth_success(client):
    """Test successful login."""
    response = client.post(login_url, json={'username': 'public', 'password': 'public'})
    assert response.status_code == 200
    assert 'token' in response.json
