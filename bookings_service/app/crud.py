# bookings_service/app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import and_

from . import models, schemas


def create_booking(db: Session, user_username: str, booking: schemas.BookingCreate):
    new_booking = models.Booking(
        user_username=user_username,
        room_id=booking.room_id,
        start_time=booking.start_time,
        end_time=booking.end_time
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking


def get_booking(db: Session, booking_id: int):
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()


def get_user_bookings(db: Session, username: str):
    return db.query(models.Booking).filter(models.Booking.user_username == username).all()


def get_all_bookings(db: Session):
    return db.query(models.Booking).all()


def update_booking(db: Session, booking_id: int, data: schemas.BookingUpdate):
    booking = get_booking(db, booking_id)
    if not booking:
        return None

    data_dict = data.dict(exclude_unset=True)
    for field, value in data_dict.items():
        setattr(booking, field, value)

    db.commit()
    db.refresh(booking)
    return booking


def delete_booking(db: Session, booking_id: int):
    booking = get_booking(db, booking_id)
    if not booking:
        return False

    db.delete(booking)
    db.commit()
    return True


def check_room_availability(db: Session, room_id: int, start_time, end_time):
    """Check if a room is already booked for the given time range"""
    conflict = db.query(models.Booking).filter(
        models.Booking.room_id == room_id,
        and_(
            models.Booking.start_time < end_time,
            models.Booking.end_time > start_time
        )
    ).first()

    return conflict is None
