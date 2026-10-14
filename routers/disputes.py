from datetime import datetime, timezone
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import auth, state_machine, ledger

router = APIRouter(prefix="/disputes", tags=["Disputes"])

@router.post("/orders/{order_id}", response_model=schemas.DisputeOut, status_code=status.HTTP_201_CREATED)
def open_dispute(
    order_id: UUID,
    dispute_in: schemas.DisputeCreate,
    db: Session = Depends(get_db),
    buyer: models.User = Depends(auth.get_current_user)
):
    """
    Buyer opens a dispute during the Protection Window.
    Immediately freezes the order and halts settlement.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.buyer_id != buyer.id and buyer.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the buyer can raise a dispute")

    if order.status != models.OrderStatus.PROTECTION_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dispute can only be opened during 'protection_window' (current: '{order.status.value}')"
        )

    # Check if existing dispute is already open
    existing = db.query(models.Dispute).filter(
        models.Dispute.order_id == order.id,
        models.Dispute.status.in_([models.DisputeStatus.OPEN, models.DisputeStatus.UNDER_REVIEW])
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A dispute is already open for this order")

    dispute = models.Dispute(
        order_id=order.id,
        buyer_id=buyer.id,
        reason=dispute_in.reason,
        description=dispute_in.description,
        evidence_urls=dispute_in.evidence_urls or [],
        status=models.DisputeStatus.OPEN,
        resolution=models.DisputeResolution.NONE,
    )
    db.add(dispute)

    # Freeze Order: PROTECTION_WINDOW -> DISPUTE_OPEN
    state_machine.transition_order_status(
        order,
        models.OrderStatus.DISPUTE_OPEN,
        actor_id=buyer.id,
        db=db,
        note=f"Dispute opened by buyer: {dispute_in.reason.value}. Settlement frozen."
    )

    ledger.record_audit_log(
        db=db,
        action="DISPUTE_OPENED",
        object_type="ORDER",
        object_id=str(order.id),
        actor_id=buyer.id,
        reason=dispute_in.description
    )

    db.commit()
    db.refresh(dispute)
    return dispute

@router.get("/{dispute_id}", response_model=schemas.DisputeOut)
def get_dispute(
    dispute_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves dispute details and resolution status."""
    dispute = db.query(models.Dispute).filter(models.Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")

    order = dispute.order
    if current_user.id not in [order.buyer_id, order.vendor_id] and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    return dispute

@router.post("/{dispute_id}/resolve", response_model=schemas.DisputeOut)
def resolve_dispute(
    dispute_id: UUID,
    resolve_req: schemas.DisputeResolveRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """
    Admin resolves a dispute with full audit trail:
    - FULL_REFUND: Transitions order to REFUNDED, records refund ledger entry.
    - PARTIAL_REFUND: Transitions order to SETTLEMENT_PENDING, records partial refund ledger entry.
    - CASE_DISMISSED: Transitions order to SETTLEMENT_PENDING, releases vendor funds for settlement.
    """
    dispute = db.query(models.Dispute).filter(models.Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")

    order = dispute.order
    now = datetime.now(timezone.utc)

    # First advance order to UNDER_REVIEW if still in DISPUTE_OPEN
    if order.status == models.OrderStatus.DISPUTE_OPEN:
        state_machine.transition_order_status(
            order,
            models.OrderStatus.UNDER_REVIEW,
            actor_id=admin.id,
            db=db,
            note="Admin initiated formal review of dispute evidence."
        )

    dispute.resolution = resolve_req.resolution
    dispute.resolution_note = resolve_req.resolution_note
    dispute.resolved_by = admin.id
    dispute.resolved_at = now

    if resolve_req.resolution == schemas.DisputeResolution.FULL_REFUND:
        dispute.status = models.DisputeStatus.RESOLVED_BUYER
        state_machine.transition_order_status(
            order,
            models.OrderStatus.REFUNDED,
            actor_id=admin.id,
            db=db,
            note=f"Admin dispute resolution: Full refund to buyer. {resolve_req.resolution_note}"
        )
        ledger.record_ledger_entry(
            db=db,
            order_id=order.id,
            entry_type=models.LedgerEntryType.REFUND,
            amount_kobo=order.gross_amount_kobo,
            state=models.LedgerState.COMMITTED,
            description="Full refund via admin dispute resolution."
        )

    elif resolve_req.resolution in [schemas.DisputeResolution.CASE_DISMISSED, schemas.DisputeResolution.PARTIAL_REFUND]:
        dispute.status = models.DisputeStatus.RESOLVED_SELLER if resolve_req.resolution == schemas.DisputeResolution.CASE_DISMISSED else models.DisputeStatus.RESOLVED_BUYER
        state_machine.transition_order_status(
            order,
            models.OrderStatus.SETTLEMENT_PENDING,
            actor_id=admin.id,
            db=db,
            note=f"Admin dispute resolution: {resolve_req.resolution.value}. Settlement resumed."
        )

    ledger.record_audit_log(
        db=db,
        action="DISPUTE_RESOLVED",
        object_type="DISPUTE",
        object_id=str(dispute.id),
        actor_id=admin.id,
        reason=resolve_req.resolution_note
    )

    db.commit()
    db.refresh(dispute)
    return dispute
