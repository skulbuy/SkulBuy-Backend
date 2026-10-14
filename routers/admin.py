from datetime import datetime, timezone
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import auth, state_machine, ledger

router = APIRouter(prefix="/admin", tags=["Admin & Ops Queue"])

@router.get("/orders", response_model=List[schemas.OrderOut])
def list_admin_orders(
    order_status: Optional[models.OrderStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """Admin queue: view and monitor all platform orders."""
    query = db.query(models.Order)
    if order_status:
        query = query.filter(models.Order.status == order_status)
    return query.order_by(models.Order.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/disputes", response_model=List[schemas.DisputeOut])
def list_admin_disputes(
    status_filter: Optional[models.DisputeStatus] = Query(None),
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """Admin queue: open and active disputes requiring manual resolution."""
    query = db.query(models.Dispute)
    if status_filter:
        query = query.filter(models.Dispute.status == status_filter)
    return query.order_by(models.Dispute.created_at.desc()).all()

@router.get("/audit-logs", response_model=List[schemas.AuditLogOut])
def list_audit_logs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """Immutable audit trail of critical operational and financial events."""
    return db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/vendors/pending", response_model=List[schemas.VendorOut])
def list_pending_vendors(
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """Admin queue: vendors awaiting verification level upgrade."""
    return db.query(models.VendorProfile).filter(models.VendorProfile.verification_level < 2).all()

@router.patch("/vendors/{vendor_id}/verify", response_model=schemas.VendorOut)
def verify_vendor(
    vendor_id: UUID,
    level: int = Query(..., ge=0, le=2, description="New verification level (0, 1, or 2)"),
    payout_account_ref: Optional[str] = Query(None, description="Paystack subaccount/recipient code"),
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """Admin approves or upgrades a vendor's verification level and payout account."""
    profile = db.query(models.VendorProfile).filter(models.VendorProfile.id == vendor_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    old_level = profile.verification_level
    profile.verification_level = level
    if payout_account_ref:
        profile.payout_account_ref = payout_account_ref

    ledger.record_audit_log(
        db=db,
        action="VENDOR_VERIFICATION_UPDATED",
        object_type="VENDOR",
        object_id=str(profile.id),
        actor_id=admin.id,
        old_value={"level": old_level},
        new_value={"level": level, "payout_ref": payout_account_ref}
    )

    db.commit()
    db.refresh(profile)
    return profile

@router.post("/settlements/batch-process")
def process_settlement_batch(
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """
    Daily batch settlement job:
    1. Checks orders where protection window has elapsed and no open dispute exists.
    2. Transitions them from PROTECTION_WINDOW -> SETTLEMENT_PENDING -> SETTLED.
    3. Records vendor payout entry in transaction ledger.
    """
    now = datetime.now(timezone.utc)
    eligible_orders = db.query(models.Order).filter(
        models.Order.status == models.OrderStatus.PROTECTION_WINDOW,
        models.Order.protection_window_ends_at <= now
    ).all()

    settled_count = 0
    for order in eligible_orders:
        # Check if open dispute exists
        has_open_dispute = db.query(models.Dispute).filter(
            models.Dispute.order_id == order.id,
            models.Dispute.status.in_([models.DisputeStatus.OPEN, models.DisputeStatus.UNDER_REVIEW])
        ).first()

        if has_open_dispute:
            continue

        # Step 1: PROTECTION_WINDOW -> SETTLEMENT_PENDING
        state_machine.transition_order_status(
            order,
            models.OrderStatus.SETTLEMENT_PENDING,
            actor_id=admin.id,
            db=db,
            note="Protection window elapsed without disputes. Ready for settlement payout."
        )

        # Step 2: SETTLEMENT_PENDING -> SETTLED
        state_machine.transition_order_status(
            order,
            models.OrderStatus.SETTLED,
            actor_id=admin.id,
            db=db,
            note="Vendor payout approved in daily settlement batch."
        )

        vendor_payout_amount = order.gross_amount_kobo - order.platform_fee_kobo
        ledger.record_ledger_entry(
            db=db,
            order_id=order.id,
            entry_type=models.LedgerEntryType.PAYOUT,
            amount_kobo=vendor_payout_amount,
            state=models.LedgerState.COMMITTED,
            description=f"Vendor settlement payout for order {order.id}"
        )
        settled_count += 1

    return {
        "status": "success",
        "processed_at": now.isoformat(),
        "settled_orders_count": settled_count
    }
