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

    # register main and blueprint routes so url_for resolves
    from application.boundaries.main_boundary import main_bp
    from application.boundaries.auth_boundary import auth_bp
    from application.boundaries.dashboard_boundary import dashboard_bp
    from application.boundaries.platform_boundary import platform_bp
    from application.boundaries.institution_boundary import institution_bp
    try:
        from application.boundaries.lecturer_boundary import lecturer_bp
        has_lect = True
    except Exception:
        lecturer_bp = None
        has_lect = False

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(platform_bp, url_prefix='/platform')
    app.register_blueprint(institution_bp, url_prefix='/institution')
    if has_lect and lecturer_bp:
        app.register_blueprint(lecturer_bp, url_prefix='/institution/lecturer')

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def render_nav_for_role(client, role):
    # Use test_request_context to set session.user via Jinja global for rendering
    with client.application.test_request_context('/'):
        # Simulate session.user being present in templates by setting global
        client.application.jinja_env.globals['session'] = type('S', (), {'user': {'user_type': role}})()
        resp = client.get('/')
        return resp


def test_navbar_shows_platform_dashboard_link(client):
    resp = render_nav_for_role(client, 'platform_manager')
    assert b'/platform' in resp.data


def test_navbar_shows_institution_admin_dashboard_link(client):
    resp = render_nav_for_role(client, 'institution_admin')
    assert b'/institution/dashboard' in resp.data


def test_navbar_shows_lecturer_dashboard_link(client):
    resp = render_nav_for_role(client, 'lecturer')
    # link will be under /institution/lecturer
    assert b'/institution/lecturer' in resp.data


def test_navbar_shows_main_dashboard_link_for_students(client):
    resp = render_nav_for_role(client, 'student')
    assert b'/dashboard' in resp.data
