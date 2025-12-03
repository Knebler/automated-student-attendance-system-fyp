import pytest
from flask import Flask


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Register main blueprint (health endpoint)
    from application.boundaries.main_boundary import main_bp
    app.register_blueprint(main_bp, url_prefix='')

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_without_db(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'status' in data
    # No DB configured in this test app -> status should be 'error'
    assert data['status'] == 'error'
    assert 'database' in data
