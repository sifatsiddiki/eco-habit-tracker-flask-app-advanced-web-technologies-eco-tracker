import pytest
from app import app, db, User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # create a test user
            u = User(email='t@test.com', display_name='Tester')
            u.set_password('testpass')
            db.session.add(u)
            db.session.commit()
        yield client

def test_index(client):
    rv = client.get('/')
    assert rv.status_code == 200

def test_register_login(client):
    # register
    rv = client.post('/register', data={'email':'a@b.com','password':'pass','display_name':'A'}, follow_redirects=True)
    assert b'Registration successful' in rv.data or b'Login' in rv.data