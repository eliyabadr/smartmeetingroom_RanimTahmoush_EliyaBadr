from sqlalchemy.orm import Session
from . import models, schemas

def create_notification(db: Session, message: str):
    notif = models.Notification(message=message)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

def get_notifications(db: Session):
    return db.query(models.Notification).all()
