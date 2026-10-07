import pytest
from app import app, db, User
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.drop_all()
        db.create_all()
        # create a demo user
        user = User(
            email="testuser@example.com",
            display_name="Test User",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(user)
        db.session.commit()

    with app.test_client() as client:
        yield client

def test_register_page_loads(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Register" in response.data

def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data

def test_successful_login(client):
    response = client.post(
        "/login",
        data={"email": "testuser@example.com", "password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    # After login, dashboard or similar content should appear
    assert b"Dashboard" in response.data or b"Habit" in response.data