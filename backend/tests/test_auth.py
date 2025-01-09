import pytest
from app import create_app


@pytest.fixture
def client():
    """Fixture to provide a test client."""
    app = create_app()
    with app.test_client() as client:
        yield client


def test_auth_success(client):
    """Test successful login."""
    response = client.post('http://127.0.0.1:5000/api/auth/login', json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert 'token' in response.json


def test_auth_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post('http://127.0.0.1:5000/api/auth/login', json={"username": "wrong", "password": "password"})
    assert response.status_code == 401
    assert response.json['message'] == "Invalid credentials"


def test_auth_missing_data(client):
    """Test login with missing data."""
    response = client.post('http://127.0.0.1:5000/api/auth/login', json={"username": "admin"})
    assert response.status_code == 401
    assert response.json['message'] == "Invalid credentials"
