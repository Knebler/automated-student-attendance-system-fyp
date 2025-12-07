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

    # register boundaries required for platform manager pages
    from application.boundaries.platform_boundary import platform_bp
    from application.boundaries.auth_boundary import auth_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(platform_bp, url_prefix='/platform')

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_get_pending_regs_shows_empty_when_no_db(client):
    resp = client.get('/platform/pending-registrations')
    assert resp.status_code == 200
    assert b'No pending registration requests' in resp.data


def test_post_approve_fails_without_db(client):
    resp = client.post('/platform/pending-registrations/approve/1', data={})
    # redirect back to list
    assert resp.status_code == 302 or resp.status_code == 200
    follow = client.get('/platform/pending-registrations')
    assert b'Failed to approve request' in follow.data or b'No database configured' in follow.data
