from pydantic import BaseModel

class NotificationOut(BaseModel):
    id: int
    message: str

    class Config:
        from_attributes = True
