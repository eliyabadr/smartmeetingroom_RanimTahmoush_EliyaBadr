# reviews_service/app/main.py

import jwt
from memory_profiler import profile
import cProfile
import pstats

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .database import Base, engine, get_db


# ------------------------------------------------
# APP INIT
# ------------------------------------------------
app = FastAPI(title="Reviews Service - Ranim Tahmoush")

origins = ["*"]  # allow everything for Codespaces
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
SECRET_KEY = "supersecret_ranim_key"
ALGORITHM = "HS256"

auth_scheme = HTTPBearer()   # <<<<<< CHANGED HERE


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


def get_current_user(credentials=Depends(auth_scheme)):
    token = credentials.credentials  # HTTPBearer gives object with .credentials
    username, role = decode_token(token)
    return {"username": username, "role": role}


def require_moderator_or_admin(current=Depends(get_current_user)):
    if current["role"] not in ("admin", "moderator"):
        raise HTTPException(status_code=403, detail="Admins or moderators only")
    return current

# ------------------------------------------------
# ROUTES
# ------------------------------------------------

@app.get("/")
def home():
    return {"service": "reviews", "status": "running"}


# Create review (any authenticated user)
@app.post("/reviews", response_model=schemas.ReviewOut, status_code=status.HTTP_201_CREATED)
@profile
def create_review(
    review_in: schemas.ReviewCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_review(db, current["username"], review_in)


# Get single review by ID
@app.get("/reviews/{review_id}", response_model=schemas.ReviewOut)
def get_review(review_id: int, db: Session = Depends(get_db)):
    review = crud.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


# Get all reviews for a room
@app.get("/rooms/{room_id}/reviews", response_model=list[schemas.ReviewOut])
@profile
def get_reviews_for_room(room_id: int, db: Session = Depends(get_db)):
    return crud.get_reviews_for_room(db, room_id)


# Update review (owner or admin/moderator)
@app.put("/reviews/{review_id}", response_model=schemas.ReviewOut)
@profile
def update_review(
    review_id: int,
    review_update: schemas.ReviewUpdate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review = crud.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.user_username != current["username"] and current["role"] not in ("admin", "moderator"):
        raise HTTPException(status_code=403, detail="Not allowed to edit this review")

    return crud.update_review(db, review_id, review_update)


# Delete review (owner or admin/moderator)
@app.delete("/reviews/{review_id}")
@profile
def delete_review(
    review_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review = crud.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.user_username != current["username"] and current["role"] not in ("admin", "moderator"):
        raise HTTPException(status_code=403, detail="Not allowed to delete this review")

    ok = crud.delete_review(db, review_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Review not found")

    return {"message": "Review deleted"}


# Flag a review (any authenticated user)
@app.post("/reviews/{review_id}/flag", response_model=schemas.ReviewOut)
def flag_review(
    review_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review = crud.flag_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


# Unflag a review (admin/moderator only)
@app.post("/reviews/{review_id}/unflag", response_model=schemas.ReviewOut)
def unflag_review(
    review_id: int,
    moderator=Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    review = crud.unflag_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


# List flagged reviews (admin/moderator only)
@app.get("/admin/reviews/flagged", response_model=list[schemas.ReviewOut])
def list_flagged_reviews(
    moderator=Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    return crud.get_flagged_reviews(db)


# ------------------------------------------------
# CPU PROFILING HELPER
# ------------------------------------------------
def run_profiler():
    profiler = cProfile.Profile()
    profiler.enable()
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats()


@app.get("/health")
def health():
    return {"status": "ok", "service": "reviews_service"}
