import pytest
from flask import Flask

from application.controls.auth_control import AuthControl


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    # explicitly ensure firebase is disabled
    app.config['firebase_auth'] = None
    return app


def test_authenticate_returns_disabled(app):
    result = AuthControl.authenticate_user(app, 'a@example.com', 'pw', user_type='student')
    assert result['success'] is False
    assert result.get('error_type') == 'FIREBASE_DISABLED'


def test_register_returns_disabled(app):
    result = AuthControl.register_user(app, 'a@example.com', 'pw', name='A Test')
    assert result['success'] is False
    assert result.get('error_type') == 'FIREBASE_DISABLED'


def test_verify_session_allows_dev_when_firebase_disabled(app):
    # simulate a request with no session values
    session_obj = {}
    result = AuthControl.verify_session(app, session_obj)
    assert result.get('success') is True
    assert isinstance(result.get('user'), dict)
    # user should be granted elevated dev access when Firebase is disabled
    assert result['user'].get('user_type') == 'platform_manager'
