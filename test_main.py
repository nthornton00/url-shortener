import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

from database import Base, get_db
from main import app

load_dotenv()

# Use a separate test database so we don't mess up real data
TEST_DATABASE_URL = os.getenv("DATABASE_URL").replace(
    "url_shortener", "url_shortener_test"
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the database to use test database
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ============================================================
# AUTH TESTS
# ============================================================

def test_register_user():
    res = client.post("/register", json={
        "email": "test@test.com",
        "password": "password123"
    })
    assert res.status_code == 201
    assert res.json()["message"] == "Account created for test@test.com"


def test_register_duplicate_email():
    # Register once
    client.post("/register", json={
        "email": "test@test.com",
        "password": "password123"
    })
    # Try to register again with same email
    res = client.post("/register", json={
        "email": "test@test.com",
        "password": "password123"
    })
    assert res.status_code == 409


def test_login_success():
    # Register first
    client.post("/register", json={
        "email": "test@test.com",
        "password": "password123"
    })
    # Then login
    res = client.post("/login", data={
        "username": "test@test.com",
        "password": "password123"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password():
    client.post("/register", json={
        "email": "test@test.com",
        "password": "password123"
    })
    res = client.post("/login", data={
        "username": "test@test.com",
        "password": "wrongpassword"
    })
    assert res.status_code == 401


# ============================================================
# URL SHORTENER TESTS
# ============================================================

def get_token():
    """Helper function to register and login, returns a token."""
    client.post("/register", json={
        "email": "test@test.com",
        "password": "password123"
    })
    res = client.post("/login", data={
        "username": "test@test.com",
        "password": "password123"
    })
    return res.json()["access_token"]


def test_shorten_url():
    token = get_token()
    res = client.post("/shorten",
        json={"url": "https://www.google.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 201
    assert "short_code" in res.json()
    assert res.json()["url"] == "https://www.google.com/"


def test_shorten_url_not_logged_in():
    res = client.post("/shorten",
        json={"url": "https://www.google.com"}
    )
    assert res.status_code == 401


def test_shorten_invalid_url():
    token = get_token()
    res = client.post("/shorten",
        json={"url": "not-a-url"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 422


def test_shorten_custom_code():
    token = get_token()
    res = client.post("/shorten",
        json={"url": "https://www.google.com", "custom_code": "mycode"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 201
    assert res.json()["short_code"] == "mycode"


def test_delete_url():
    token = get_token()
    # Create a link first
    res = client.post("/shorten",
        json={"url": "https://www.google.com", "custom_code": "delme"},
        headers={"Authorization": f"Bearer {token}"}
    )
    # Delete it
    res = client.delete("/shorten/delme",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 204