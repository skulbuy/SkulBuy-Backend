from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db, settings
import models
import schemas
from services import auth, utils, state_machine, ledger

router = APIRouter(prefix="/delivery", tags=["Delivery & Hub OTP Verification"])

@router.get("/orders/{order_id}/otp", response_model=schemas.DeliveryOTPResponse)
def get_order_delivery_otp(
    order_id: UUID,
    db: Session = Depends(get_db),
    buyer: models.User = Depends(auth.get_current_user)
):
    """
    Retrieves the delivery OTP for the buyer.
    Only the buyer can access their OTP.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.buyer_id != buyer.id and buyer.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the buyer can view the delivery OTP")

    delivery = db.query(models.Delivery).filter(models.Delivery.order_id == order.id).first()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery record not found")

    raw_otp = (delivery.device_meta or {}).get("raw_otp_cache", "******")

    return schemas.DeliveryOTPResponse(
        order_id=order.id,
        otp=raw_otp,
    )

@router.post("/orders/{order_id}/verify-otp", response_model=schemas.DeliveryOut)
def verify_delivery_otp(
    order_id: UUID,
    req: schemas.DeliveryVerifyOTPRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Pickup Hub OTP verification endpoint.
    1. Validates OTP against secure SHA-256 hash.
    2. Logs device/terminal metadata.
    3. Transitions order: AT_PICKUP_HUB -> DELIVERY_VERIFIED -> PROTECTION_WINDOW.
    4. Starts protection countdown window.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status != models.OrderStatus.AT_PICKUP_HUB:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order must be 'at_pickup_hub' to verify handover (current: '{order.status.value}')"
        )

    delivery = db.query(models.Delivery).filter(models.Delivery.order_id == order.id).first()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery record not found")

    # Cryptographic OTP Match Verification
    if not utils.verify_otp(req.otp, delivery.otp_hash):
        ledger.record_audit_log(
            db=db,
            action="OTP_VERIFICATION_FAILED",
            object_type="ORDER",
            object_id=str(order.id),
            reason=f"Wrong OTP entered at Hub {req.hub_id}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code.")

    now = datetime.now(timezone.utc)
    delivery.verified_at = now
    delivery.device_meta = {
        "client_ip": request.client.host if request.client else "unknown",
        "terminal_info": req.terminal_info,
        "verified_hub_id": str(req.hub_id),
    }

    # Step 1: Transition to DELIVERY_VERIFIED
    state_machine.transition_order_status(
        order,
        models.OrderStatus.DELIVERY_VERIFIED,
        actor_id=None,
        db=db,
        note="Item physically handed over to buyer at Pickup Hub. OTP confirmed."
    )

    # Step 2: Transition to PROTECTION_WINDOW & Set Window Expiry
    window_hours = settings.PROTECTION_WINDOW_HOURS
    order.protection_window_ends_at = now + timedelta(hours=window_hours)

    state_machine.transition_order_status(
        order,
        models.OrderStatus.PROTECTION_WINDOW,
        actor_id=None,
        db=db,
        note=f"Protected Checkout window started ({window_hours} hours). Dispute can be filed if item has issues."
    )

    db.commit()
    db.refresh(delivery)
    return delivery
