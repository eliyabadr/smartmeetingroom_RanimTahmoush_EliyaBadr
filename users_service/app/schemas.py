from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional


# ======================================
# BASE USER MODEL
# ======================================
class UserBase(BaseModel):
    name: str
    username: str = Field(..., min_length=3)
    email: EmailStr
    role: str = "regular"


# ======================================
# CREATE USER (WITH VALIDATION)
# ======================================
class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

    @validator("password")
    def password_strength(cls, value):
        if value.isnumeric() or value.isalpha():
            raise ValueError("Password must contain letters AND numbers.")
        return value


# ======================================
# USER UPDATE (ALL OPTIONAL)
# ======================================
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    role: Optional[str] = None

    @validator("password")
    def validate_password(cls, value):
        if value and (value.isnumeric() or value.isalpha()):
            raise ValueError("Password must contain letters AND numbers.")
        return value


# ======================================
# USER OUTPUT
# ======================================
class UserOut(BaseModel):
    id: int
    name: str
    username: str
    email: EmailStr
    role: str

    class Config:
        orm_mode = True


# ======================================
# TOKEN SCHEMAS
# ======================================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
