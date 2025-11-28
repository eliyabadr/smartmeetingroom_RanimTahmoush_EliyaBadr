import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_users.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_register_user_success():
    response = client.post(
        "/register",
        json={
            "username": "ranim",
            "email": "ranim@example.com",
            "password": "123456",
            "role": "admin"
        }
    )
    assert response.status_code == 201
    assert response.json()["username"] == "ranim"


def test_register_user_duplicate():
    response = client.post(
        "/register",
        json={
            "username": "ranim",
            "email": "ranim@example.com",
            "password": "123456",
            "role": "admin"
        }
    )
    assert response.status_code == 400


def test_login_success():
    response = client.post(
        "/login",
        data={"username": "ranim", "password": "123456"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password():
    response = client.post(
        "/login",
        data={"username": "ranim", "password": "wrongpass"}
    )
    assert response.status_code == 401
