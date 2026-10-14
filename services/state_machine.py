from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import models

ALLOWED_TRANSITIONS = {
    models.OrderStatus.DRAFT: [
        models.OrderStatus.PAYMENT_PENDING,
    ],
    models.OrderStatus.PAYMENT_PENDING: [
        models.OrderStatus.PAYMENT_VERIFIED,
        models.OrderStatus.PAYMENT_FAILED,
        models.OrderStatus.PAYMENT_EXPIRED,
    ],
    models.OrderStatus.PAYMENT_VERIFIED: [
        models.OrderStatus.VENDOR_PENDING,
    ],
    models.OrderStatus.VENDOR_PENDING: [
        models.OrderStatus.VENDOR_ACCEPTED,
        models.OrderStatus.VENDOR_REJECTED,
    ],
    models.OrderStatus.VENDOR_REJECTED: [
        models.OrderStatus.REFUND_PENDING,
    ],
    models.OrderStatus.REFUND_PENDING: [
        models.OrderStatus.REFUNDED,
    ],
    models.OrderStatus.VENDOR_ACCEPTED: [
        models.OrderStatus.PREPARING,
    ],
    models.OrderStatus.PREPARING: [
        models.OrderStatus.READY_FOR_PICKUP,
    ],
    models.OrderStatus.READY_FOR_PICKUP: [
        models.OrderStatus.AT_PICKUP_HUB,
    ],
    models.OrderStatus.AT_PICKUP_HUB: [
        models.OrderStatus.DELIVERY_VERIFIED,
    ],
    models.OrderStatus.DELIVERY_VERIFIED: [
        models.OrderStatus.PROTECTION_WINDOW,
    ],
    models.OrderStatus.PROTECTION_WINDOW: [
        models.OrderStatus.DISPUTE_OPEN,
        models.OrderStatus.SETTLEMENT_PENDING,
    ],
    models.OrderStatus.DISPUTE_OPEN: [
        models.OrderStatus.UNDER_REVIEW,
    ],
    models.OrderStatus.UNDER_REVIEW: [
        models.OrderStatus.REFUNDED,
        models.OrderStatus.SETTLEMENT_PENDING,
    ],
    models.OrderStatus.SETTLEMENT_PENDING: [
        models.OrderStatus.SETTLED,
    ],
}

def transition_order_status(
    order: models.Order,
    target_status: models.OrderStatus,
    actor_id: Optional[UUID],
    db: Session,
    note: Optional[str] = None
) -> models.Order:
    """
    Validates and executes an order state machine transition.
    Enforces server-side validation against §4 of the SkulBuy MVP v2 PRD.
    Records an entry in the OrderTimeline.
    """
    allowed = ALLOWED_TRANSITIONS.get(order.status, [])
    if target_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Illegal state transition from '{order.status.value}' to '{target_status.value}'."
        )

    previous_status = order.status.value
    order.status = target_status

    # Record in immutable timeline
    timeline_entry = models.OrderTimeline(
        order_id=order.id,
        from_status=previous_status,
        to_status=target_status.value,
        actor_id=actor_id,
        note=note,
    )
    db.add(timeline_entry)
    db.commit()
    db.refresh(order)

    return order
