from pydantic import BaseModel, Field
from typing import Optional


# ======================================
# BASE REVIEW SCHEMA
# ======================================
class ReviewBase(BaseModel):
    room_id: int = Field(..., description="ID of the room being reviewed")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: str = Field(..., min_length=2, max_length=500, description="Review comment")


# ======================================
# CREATE REVIEW
# ======================================
class ReviewCreate(ReviewBase):
    pass


# ======================================
# UPDATE REVIEW (OPTIONAL FIELDS)
# ======================================
class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, min_length=2, max_length=500)


# ======================================
# OUTPUT REVIEW MODEL
# ======================================
class ReviewOut(BaseModel):
    id: int
    room_id: int
    user_username: str
    rating: int
    comment: str
    flagged: bool

    class Config:
        orm_mode = True
