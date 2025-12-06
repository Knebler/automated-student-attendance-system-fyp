import pytest
import os
from flask import Flask


@pytest.fixture
def app():
    # create a minimal Flask app and register the dev blueprint
    # ensure Flask can find project-level templates during tests
    templates_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app = Flask(__name__, template_folder=templates_path)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    # Ensure templates referencing csrf_token() don't fail in tests
    app.jinja_env.globals['csrf_token'] = lambda: ''

    # import and register dev blueprint and some layout blueprints to make templates work
    from application.boundaries.dev_boundary import dev_bp
    from application.boundaries.main_boundary import main_bp
    from application.boundaries.auth_boundary import auth_bp
    from application.boundaries.dashboard_boundary import dashboard_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(dev_bp, url_prefix='/dev')

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_get_dev_page(client):
    resp = client.get('/dev/test-endpoint')
    assert resp.status_code == 200
    # ensure dynamic actions are present (at least echo)
    assert b'Dev' in resp.data
    assert b'echo' in resp.data
    # actions registered from boundaries/controls should also be present
    for name in [
        'init_database', 'mark_attendance', 'get_session_attendance',
        'get_student_attendance_summary', 'check_table_has_data', 'insert_sample_data',
        'create_institution', 'get_institution_stats', 'get_user_by_email_and_type',
        'register_institution', 'register_user', 'authenticate_user'
    ]:
        assert name.encode() in resp.data


def test_post_echo_action(client):
    resp = client.post('/dev/test-endpoint', data={'action': 'echo', 'message': 'hello world'})
    assert resp.status_code == 200
    assert resp.data == b'hello world'
    assert resp.headers.get('Content-Type', '').startswith('text/plain')


def test_post_unknown_action(client):
    resp = client.post('/dev/test-endpoint', data={'action': 'this_does_not_exist'})
    assert resp.status_code == 400
    assert b'Unknown action' in resp.data
