import pytest
from app import create_app, config


@pytest.fixture(scope='module')
def client():
    """Fixture to provide a test client."""
    config.TESTING = True
    config.DEBUG = False
    server = create_app()
    with server.test_client() as client:
        with server.app_context():
            yield client
