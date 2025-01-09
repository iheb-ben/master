import pytest
from app import create_app, config


@pytest.fixture(scope='module')
def client():
    """Fixture to provide a test client."""
    config.TESTING = True
    config.DEBUG = False
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            yield client
