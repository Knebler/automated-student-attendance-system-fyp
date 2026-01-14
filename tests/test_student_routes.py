import os
import pytest

from flask import Flask
from application.controls.attendance_control import AttendanceControl
from application.controls.auth_control import AuthControl


@pytest.fixture
def app():
    templates_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app = Flask(__name__, template_folder=templates_path)
    app.config['TESTING'] = True
    app.jinja_env.globals['csrf_token'] = lambda: ''

    # register the student blueprint
    from application.boundaries.student_boundary import student_bp
    app.register_blueprint(student_bp, url_prefix='/student')

    # register auth blueprint used by templates (login/logout links)
    from application.boundaries.auth_boundary import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # minimal main blueprint used by templates
    from flask import Blueprint
    main = Blueprint('main', __name__)

    @main.route('/')
    def home():
        return 'home'

    @main.route('/features')
    def features():
        return 'features'

    @main.route('/about')
    def about():
        return 'about'

    @main.route('/subscriptions')
    def subscriptions():
        return 'subscriptions'

    @main.route('/testimonials')
    def testimonials():
        return 'testimonials'

    @main.route('/faq')
    def faq():
        return 'faq'

    app.register_blueprint(main)

    # Secret key required for session/flash in tests
    app.secret_key = 'test-secret'

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_student_attendance_pages_render(client, monkeypatch):
    # Mock the AuthControl to simulate a logged in student
    monkeypatch.setattr(AuthControl, 'verify_session', staticmethod(lambda app, sess: {'success': True, 'user': {'user_id': 1, 'name': 'Test Student'}}))

    # Mock attendance summary
    monkeypatch.setattr(AttendanceControl, 'get_student_attendance_summary', staticmethod(lambda app, user_id, days=30: {'success': True, 'summary': {'present_pct': 90}, 'attendance_records': []}))

    resp = client.get('/student/attendance')
    assert resp.status_code == 200
    assert b'My Attendance' in resp.data

    resp = client.get('/student/attendance/history')
    assert resp.status_code == 200
    assert b'Attendance History' in resp.data

    resp = client.get('/student/attendance/checkin')
    assert resp.status_code == 200
    assert b'Class Check-In' in resp.data

    resp = client.get('/student/attendance/checkin/face')
    assert resp.status_code == 200
    assert b'Face' in resp.data or b'Check-In' in resp.data

    resp = client.get('/student/appeal')
    assert resp.status_code == 200

    resp = client.get('/student/appeal/form')
    assert resp.status_code == 200
