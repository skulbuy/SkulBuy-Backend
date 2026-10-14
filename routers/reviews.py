from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import auth

router = APIRouter(prefix="/reviews", tags=["Reviews & Ratings"])

@router.post("/orders/{order_id}", response_model=schemas.ReviewOut, status_code=status.HTTP_201_CREATED)
def leave_review(
    order_id: UUID,
    review_in: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    reviewer: models.User = Depends(auth.get_current_user)
):
    """
    Leaves a review and 1-5 star rating for an order.
    Allowed after delivery has been verified or settled.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if reviewer.id not in [order.buyer_id, order.vendor_id]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be party to the order")

    # Only allow reviews once delivery is verified or later
    allowed_statuses = [
        models.OrderStatus.DELIVERY_VERIFIED,
        models.OrderStatus.PROTECTION_WINDOW,
        models.OrderStatus.SETTLEMENT_PENDING,
        models.OrderStatus.SETTLED,
    ]
    if order.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reviews can only be submitted after delivery is confirmed."
        )

    # Check for existing review by this reviewer for this order
    existing = db.query(models.Review).filter(
        models.Review.order_id == order.id,
        models.Review.reviewer_id == reviewer.id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already reviewed this order")

    reviewee_id = order.vendor_id if reviewer.id == order.buyer_id else order.buyer_id

    review = models.Review(
        order_id=order.id,
        reviewer_id=reviewer.id,
        reviewee_id=reviewee_id,
        rating=review_in.rating,
        comment=review_in.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

@router.get("/users/{user_id}", response_model=List[schemas.ReviewOut])
def get_user_reviews(user_id: UUID, db: Session = Depends(get_db)):
    """Retrieves all reviews received by a student or vendor."""
    return db.query(models.Review).filter(models.Review.reviewee_id == user_id).order_by(models.Review.created_at.desc()).all()
