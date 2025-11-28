from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ======================================
# BASE BOOKING SCHEMA
# ======================================
class BookingBase(BaseModel):
    room_id: int
    start_time: datetime
    end_time: datetime


# ======================================
# CREATE BOOKING
# ======================================
class BookingCreate(BookingBase):
    pass


# ======================================
# UPDATE BOOKING (OPTIONAL FIELDS)
# ======================================
class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# ======================================
# BOOKING OUTPUT
# ======================================
class BookingOut(BookingBase):
    id: int
    user_username: str

    class Config:
        orm_mode = True
