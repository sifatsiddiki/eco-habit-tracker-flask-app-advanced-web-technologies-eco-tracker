import pytest
from app import app, db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200

def test_dashboard_redirects_when_not_logged_in(client):
    response = client.get("/dashboard", follow_redirects=True)
    # Should eventually lead to login page
    assert response.status_code == 200
    assert b"Login" in response.data or b"Register" in response.data

def test_register_post_missing_data(client):
    response = client.post("/register", data={}, follow_redirects=True)
    # Should not crash; respond with a page
    assert response.status_code == 200