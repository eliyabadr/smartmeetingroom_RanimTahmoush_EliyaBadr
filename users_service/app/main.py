# users_service/app/main.py

from datetime import datetime, timedelta
from typing import List

from memory_profiler import profile
import cProfile
import pstats

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas, crud
from .database import Base, engine, get_db


# ------------------------------------------------
# APP INIT
# ------------------------------------------------
app = FastAPI(title="Users Service - Ranim Tahmoush")

# For simplicity, allow all origins (you can restrict later)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


# ------------------------------------------------
# SECURITY / JWT
# ------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "supersecret_ranim_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# IMPORTANT: tokenUrl is only used by Users Swagger for /login
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="https://shiny-train-g47pjxrpjpr6c9r65-8001.app.github.dev/login"
)



# ------------------------------------------------
# PASSWORD UTILS
# ------------------------------------------------
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ------------------------------------------------
# ACCESS TOKEN CREATION
# ------------------------------------------------
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ------------------------------------------------
# JWT DECODE WITH FULL ERROR HANDLING
# ------------------------------------------------
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token: missing subject")

        return username, role

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    username, role = decode_token(token)

    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return current_user


# ------------------------------------------------
# ROUTES
# ------------------------------------------------

@app.get("/")
def home():
    return {"service": "users", "status": "running"}


# REGISTER USER
@app.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
@profile
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    if crud.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed_pw = get_password_hash(user_in.password)
    db_user = crud.create_user(db, user_in, hashed_password=hashed_pw)
    return db_user


# LOGIN
@app.post("/login", response_model=schemas.Token)
@profile
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_username(db, form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token({"sub": user.username, "role": user.role})

    return {"access_token": access_token, "token_type": "bearer"}


# GET SELF
@app.get("/me", response_model=schemas.UserOut)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


# ADMIN GET ALL USERS
@app.get("/admin/users", response_model=List[schemas.UserOut])
def admin_list_users(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return crud.get_users(db)


# GET USER BY USERNAME
@app.get("/users/{username}", response_model=schemas.UserOut)
def get_user(
    username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# UPDATE USER
@app.put("/users/{username}", response_model=schemas.UserOut)
def update_user(
    username: str,
    update_data: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.username != username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    if update_data.password:
        update_data.password = get_password_hash(update_data.password)

    user = crud.update_user(db, username, update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# DELETE USER
@app.delete("/users/{username}")
def delete_user(
    username: str,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ok = crud.delete_user(db, username)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User '{username}' deleted"}


# ------------------------------------------------
# CUSTOM OPENAPI
# ------------------------------------------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Users Service - Ranim Tahmoush",
        version="1.0.0",
        description="Users microservice with JWT authentication and PostgreSQL.",
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/health")
def health():
    return {"status": "ok", "service": "users_service"}
