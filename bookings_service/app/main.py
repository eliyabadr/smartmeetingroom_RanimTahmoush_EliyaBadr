import os
import json
import requests
import jwt
import pika  # RABBITMQ
from memory_profiler import profile
import cProfile
import pstats

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

#from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .database import Base, engine, get_db


# ------------------------------------------------
# APP INIT
# ------------------------------------------------
app = FastAPI(title="Bookings Service - Ranim Tahmoush")

Base.metadata.create_all(bind=engine)

SECRET_KEY = "supersecret_ranim_key"
ALGORITHM = "HS256"

#oauth2_scheme = OAuth2PasswordBearer(
#    tokenUrl="https://shiny-train-g47pjxrpjpr6c9r65-8001.app.github.dev/login"
#)
auth_scheme = HTTPBearer()  

# ------------------------------------------------
# JWT DECODE
# ------------------------------------------------
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: no subject")

        return username, role

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials  # extract raw token
    username, role = decode_token(token)
    return {"username": username, "role": role}


def require_admin(current=Depends(get_current_user)):
    if current["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return current


# ------------------------------------------------
# RABBITMQ HELPER
# ------------------------------------------------
def publish_booking_message(booking_data: dict):
    """Publish a booking event to RabbitMQ queue."""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST", "rabbitmq"))
        )
        channel = connection.channel()

        channel.queue_declare(queue="booking_notifications")

        channel.basic_publish(
            exchange="",
            routing_key="booking_notifications",
            body=json.dumps(booking_data),
        )

        connection.close()

    except Exception as e:
        print("❌ RabbitMQ publish error:", e)
        # (We do NOT raise; booking should succeed even without MQ)


# ------------------------------------------------
# ROOM SERVICE CHECK
# ------------------------------------------------
def room_exists(room_id: int):
    try:
        response = requests.get(f"http://rooms_service:8002/rooms/{room_id}", timeout=3)

        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False

        return False

    except:
        raise HTTPException(
            status_code=502,
            detail="Rooms service unavailable",
        )


@app.get("/")
def home():
    return {"service": "bookings", "status": "running"}


# ------------------------------------------------
# CREATE BOOKING
# ------------------------------------------------
@app.post("/bookings", response_model=schemas.BookingOut, status_code=201)
def create_booking(
    booking: schemas.BookingCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate time order
    if booking.end_time <= booking.start_time:
        raise HTTPException(
            status_code=400, detail="end_time must be after start_time"
        )

    # Validate room exists
    if not room_exists(booking.room_id):
        raise HTTPException(status_code=404, detail="Room not found")

    # Validate availability
    available = crud.check_room_availability(
        db, booking.room_id, booking.start_time, booking.end_time
    )
    if not available:
        raise HTTPException(status_code=400, detail="Room already booked")

    # Create booking
    created = crud.create_booking(db, current["username"], booking)

    # Publish async MQ event
    publish_booking_message(
        {
            "event": "booking_created",
            "username": current["username"],
            "room_id": booking.room_id,
            "start": str(booking.start_time),
            "end": str(booking.end_time),
        }
    )

    return created


# ------------------------------------------------
# GET USER BOOKINGS
# ------------------------------------------------
@app.get("/users/{username}/bookings", response_model=list[schemas.BookingOut])
def get_user_bookings(
    username: str,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current["username"] != username and current["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    return crud.get_user_bookings(db, username)


# ------------------------------------------------
# GET A SPECIFIC BOOKING
# ------------------------------------------------
@app.get("/bookings/{booking_id}", response_model=schemas.BookingOut)
def get_booking(
    booking_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = crud.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_username != current["username"] and current["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    return booking


# ------------------------------------------------
# UPDATE BOOKING
# ------------------------------------------------
@app.put("/bookings/{booking_id}", response_model=schemas.BookingOut)
def update_booking(
    booking_id: int,
    booking_update: schemas.BookingUpdate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = crud.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_username != current["username"] and current["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    new_start = booking_update.start_time or booking.start_time
    new_end = booking_update.end_time or booking.end_time

    if new_end <= new_start:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    available = crud.check_room_availability(
        db, booking.room_id, new_start, new_end
    )
    if not available:
        raise HTTPException(status_code=400, detail="Time conflict")

    updated = crud.update_booking(db, booking_id, booking_update)

    # Publish update event
    publish_booking_message(
        {
            "event": "booking_updated",
            "username": booking.user_username,
            "room_id": booking.room_id,
            "start": str(new_start),
            "end": str(new_end),
        }
    )

    return updated


# ------------------------------------------------
# DELETE BOOKING
# ------------------------------------------------
@app.delete("/bookings/{booking_id}")
def delete_booking(
    booking_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = crud.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_username != current["username"] and current["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    crud.delete_booking(db, booking_id)

    # Publish deletion event
    publish_booking_message(
        {
            "event": "booking_deleted",
            "username": booking.user_username,
            "room_id": booking.room_id,
        }
    )

    return {"message": "Booking deleted"}


# ------------------------------------------------
# CPU PROFILER
# ------------------------------------------------
def run_profiler():
    profiler = cProfile.Profile()
    profiler.enable()
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.strip_dirs().sort_stats("cumulative").print_stats()


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")   # simple DB check
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "service": "bookings_service",
        "status": "ok",
        "database": db_ok,
        "rabbitmq_host": os.getenv("RABBITMQ_HOST", "rabbitmq")
    }
