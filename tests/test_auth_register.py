import os
import pytest
from flask import Flask


@pytest.fixture
def app():
    templates_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app = Flask(__name__, template_folder=templates_path)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.jinja_env.globals['csrf_token'] = lambda: ''

    from application.boundaries.auth_boundary import auth_bp
    from application.boundaries.main_boundary import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_get_register_contains_institution_field(client):
    resp = client.get('/auth/register')
    assert resp.status_code == 200
    assert b'Educational Institute' in resp.data


def test_post_non_admin_is_rejected(client):
    resp = client.post('/auth/register', data={
        'name': 'Alice Admin',
        'email': 'a@x.com',
        'password': 'password',
        'role': 'student'
    })
    # Should render page again with a warning message
    assert resp.status_code == 200
    assert b'Registration is restricted to Institution Admins only' in resp.data


def test_post_admin_missing_institution(client):
    resp = client.post('/auth/register', data={
        'name': 'Alice Admin',
        'email': 'a@x.com',
        'password': 'password',
        'role': 'institution_admin'
    })
    assert resp.status_code == 200
    assert b'Educational Institute name is required' in resp.data


def test_post_admin_with_institution_attempt_returns_failure_without_db(client):
    resp = client.post('/auth/register', data={
        'name': 'Alice Admin',
        'email': 'a@x.com',
        'password': 'password',
        'role': 'institution_admin',
        'institution_name': 'Example University'
    })
    # No DB configured in test app -> registration attempt should show a failure message
    assert resp.status_code == 200
    assert (b'Failed to submit registration request' in resp.data) or (b'No database configured' in resp.data)
