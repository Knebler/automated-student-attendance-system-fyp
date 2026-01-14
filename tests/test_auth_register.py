import os
import pytest

from flask import Flask
from application.controls.auth_control import AuthControl
from application.entities.base_entity import BaseEntity


@pytest.fixture
def app():
    templates_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app = Flask(__name__, template_folder=templates_path)
    app.config['TESTING'] = True
    app.jinja_env.globals['csrf_token'] = lambda: ''

    # register the auth blueprint
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


def test_register_form_shows_institutions(client, monkeypatch):
    # Mock the BaseEntity.execute_query to return an institution list
    monkeypatch.setattr(BaseEntity, 'execute_query', lambda app, q, params=None, fetch_one=False, fetch_all=False: [(1, 'Example University')])

    resp = client.get('/auth/register')
    assert resp.status_code == 200
    assert b'Select your Institution' in resp.data
    assert b'Example University' in resp.data


def test_register_post_student_creates_local_and_firebase(client, monkeypatch):
    # Mock the institution list
    monkeypatch.setattr(BaseEntity, 'execute_query', lambda app, q, params=None, fetch_one=False, fetch_all=False: [(1, 'Example University')])

    # Mock Firebase register_user to return success
    monkeypatch.setattr(AuthControl, 'register_user', lambda app, email, password, name=None, role='student': {'success': True, 'firebase_uid': 'uid-1'})

    # Mock Student.get_model so it does not try to initialize SQLAlchemy
    from application.entities.student import Student
    monkeypatch.setattr(Student, 'get_model', classmethod(lambda cls: object()))

    # Mock BaseEntity.create to simulate local record creation
    created = {'student_id': 1}
    monkeypatch.setattr(BaseEntity, 'create', lambda app, model, data: created)

    resp = client.post('/auth/register', data={
        'name': 'Test Student',
        'email': 'test@student.edu',
        'password': 'password1',
        'role': 'student',
        'institution_id': '1'
    }, follow_redirects=True)

    assert resp.status_code in (200, 302)
    assert b'Registration successful' in resp.data
