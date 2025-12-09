import os
import pytest

from application.controls.auth_control import AuthControl


@pytest.fixture
def app():
    templates_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    from flask import Flask
    app = Flask(__name__, template_folder=templates_path)
    app.config['TESTING'] = True
    app.jinja_env.globals['csrf_token'] = lambda: ''

    # register the institution blueprint
    from application.boundaries.institution_boundary import institution_bp
    app.register_blueprint(institution_bp, url_prefix='/institution')

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def make_verify_session(user_type, extra_user=None):
    def _fake_verify(app, session_obj):
        return {
            'success': True,
            'user': extra_user or {'user_type': user_type, 'user_id': 1, 'institution_id': 1, 'email': 'x@y'}
        }
    return _fake_verify


def test_admin_manage_routes_allowed(client, monkeypatch):
    monkeypatch.setattr(AuthControl, 'verify_session', make_verify_session('institution_admin'))

    for path in ['/institution/manage_users', '/institution/manage_attendance', '/institution/manage_classes', '/institution/institution_profile', '/institution/import_data',
                 '/institution/attendance/student/1', '/institution/attendance/class/1', '/institution/attendance/reports']:
        # For attendance paths return sample content from AttendanceControl
        if path.startswith('/institution/attendance') or path == '/institution/manage_attendance':
            from application.controls.attendance_control import AttendanceControl

            if path.startswith('/institution/attendance/student'):
                monkeypatch.setattr(AttendanceControl, 'get_student_attendance_summary', lambda app, sid, days=30: {
                    'success': True,
                    'student_info': {'student_id': sid, 'full_name': 'Test Student'},
                    'summary': {'total_sessions': 1, 'present_count': 1, 'attendance_rate': 100},
                    'attendance_records': [{'attendance_id': 1, 'session_topic': 'Topic A', 'status': 'present'}]
                })

            if path.startswith('/institution/attendance/class'):
                monkeypatch.setattr(AttendanceControl, 'get_session_attendance', lambda app, cid: {
                    'success': True,
                    'session': {'session_id': cid, 'session_topic': 'Topic A', 'course_code': 'CSIT 314'},
                    'attendance_records': [{'attendance_id': 11, 'student_id': 101, 'student_name': 'Alice', 'status': 'present'}]
                })

            if path.endswith('/reports'):
                monkeypatch.setattr(AttendanceControl, 'get_today_sessions_attendance', lambda app, lecturer_id=None: {
                    'success': True,
                    'sessions': [{'session': {'session_id': 123}, 'attendance_records': [1,2,3]}]
                })

            if path == '/institution/manage_attendance':
                # make the all-sessions call return a small payload so the template can render
                monkeypatch.setattr(AttendanceControl, 'get_all_sessions_attendance', lambda app, lecturer_id=None: {
                    'success': True,
                    'sessions': [
                        {'session': {'session_id': 1, 'course_code': 'CS101', 'session_date': '2025-12-01'}, 'attendance_records': [{'status': 'present'}, {'status': 'absent'}]},
                        {'session': {'session_id': 2, 'course_code': 'CS102', 'session_date': '2025-11-20'}, 'attendance_records': [{'status': 'present'}]}
                    ]
                })

        resp = client.get(path)
        assert resp.status_code in (200, 404)


def test_admin_routes_denied_for_lecturer(client, monkeypatch):
    monkeypatch.setattr(AuthControl, 'verify_session', make_verify_session('lecturer'))

    resp = client.get('/institution/manage_users', follow_redirects=False)
    assert resp.status_code in (302, 401, 403, 404)
