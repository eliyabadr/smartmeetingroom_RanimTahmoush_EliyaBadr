# users_service/app/crud.py
from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session) -> List[models.User]:
    return db.query(models.User).all()

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str) -> models.User:
    db_user = models.User(
        name=user.name,
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, username: str, update_data: schemas.UserUpdate) -> Optional[models.User]:
    user = get_user_by_username(db, username)
    if not user:
        return None

    if update_data.name is not None:
        user.name = update_data.name
    if update_data.email is not None:
        user.email = update_data.email
    if update_data.role is not None:
        user.role = update_data.role
    if update_data.password is not None:
        user.hashed_password = update_data.password  # should already be hashed

    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, username: str) -> bool:
    user = get_user_by_username(db, username)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True




def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user