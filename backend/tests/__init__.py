import pytest
from app import create_app


@pytest.fixture
def client():
    """Fixture to provide a test client."""
    app = create_app()
    app.config['DEBUG'] = False
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


from . import test_auth
