from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.sql import func
from .database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_username = Column(String, nullable=False, index=True)
    room_id = Column(Integer, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Index to speed up "is this room booked in this time window?"
Index(
    "ix_bookings_room_time_window",
    Booking.room_id,
    Booking.start_time,
    Booking.end_time,
)
