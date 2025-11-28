# bookings_service/app/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load DATABASE_URL from docker-compose environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback ONLY when running outside docker-compose
if not DATABASE_URL:
    # IMPORTANT: use the docker-compose service name, NOT localhost
    DATABASE_URL = "postgresql+psycopg2://ranim:password123@postgres:5432/smartmeeting"

# Create engine with correct URL
engine = create_engine(DATABASE_URL)

# SQLAlchemy session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Session dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
