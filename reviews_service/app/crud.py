# reviews_service/app/crud.py
from sqlalchemy.orm import Session

from . import models, schemas


def create_review(db: Session, user_username: str, review_in: schemas.ReviewCreate):
    review = models.Review(
        room_id=review_in.room_id,
        user_username=user_username,
        rating=review_in.rating,
        comment=review_in.comment.strip(),  # simple sanitization
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_review(db: Session, review_id: int):
    return db.query(models.Review).filter(models.Review.id == review_id).first()


def get_reviews_for_room(db: Session, room_id: int):
    return db.query(models.Review).filter(models.Review.room_id == room_id).all()


def update_review(db: Session, review_id: int, data: schemas.ReviewUpdate):
    review = get_review(db, review_id)
    if not review:
        return None

    data_dict = data.dict(exclude_unset=True)
    if "comment" in data_dict and data_dict["comment"] is not None:
        data_dict["comment"] = data_dict["comment"].strip()

    for field, value in data_dict.items():
        setattr(review, field, value)

    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review_id: int) -> bool:
    review = get_review(db, review_id)
    if not review:
        return False
    db.delete(review)
    db.commit()
    return True


def flag_review(db: Session, review_id: int) -> models.Review | None:
    review = get_review(db, review_id)
    if not review:
        return None
    review.flagged = True
    db.commit()
    db.refresh(review)
    return review


def unflag_review(db: Session, review_id: int) -> models.Review | None:
    review = get_review(db, review_id)
    if not review:
        return None
    review.flagged = False
    db.commit()
    db.refresh(review)
    return review


def get_flagged_reviews(db: Session):
    return db.query(models.Review).filter(models.Review.flagged == True).all()
