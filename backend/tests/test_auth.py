from tests import client
from app.config import SERVER_NAME


def test_auth_success(client):
    """Test successful login."""
    response = client.post(f'http://{SERVER_NAME}/api/auth/login', json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert 'token' in response.json


def test_auth_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(f'http://{SERVER_NAME}/api/auth/login', json={"username": "wrong", "password": "password"})
    assert response.status_code == 401
    assert response.json['message'] == ResponseMessages.INVALID_CREDENTIALS.value


def test_auth_missing_data(client):
    """Test login with missing data."""
    response = client.post(f'http://{SERVER_NAME}/api/auth/login', json={"username": "admin"})
    assert response.status_code == 400
