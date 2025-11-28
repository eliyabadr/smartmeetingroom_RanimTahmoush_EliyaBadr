import pytest
from fastapi.testclient import TestClient
from app.main import app, SECRET_KEY
from app.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
import jwt

SQLALCHEMY_TEST_URL = "sqlite:///./test_reviews.db"

engine = create_engine(
    SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False}
)
TestingDB = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_db():
    try:
        db = TestingDB()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_db
client = TestClient(app)

user_token = jwt.encode({"sub": "ranim", "role": "user"}, SECRET_KEY, algorithm="HS256")
headers_user = {"Authorization": f"Bearer {user_token}"}

def test_get_reviews_empty():
    response = client.get("/reviews/room/1")
    assert response.status_code == 200
    assert response.json() == []
