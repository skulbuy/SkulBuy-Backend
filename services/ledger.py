from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import models

def record_ledger_entry(
    db: Session,
    order_id: UUID,
    entry_type: models.LedgerEntryType,
    amount_kobo: int,
    provider_ref: Optional[str] = None,
    state: models.LedgerState = models.LedgerState.COMMITTED,
    description: Optional[str] = None
) -> models.TransactionLedger:
    """
    Appends an immutable entry to the transaction ledger.
    The transaction ledger is the single financial source of truth.
    """
    entry = models.TransactionLedger(
        order_id=order_id,
        type=entry_type,
        amount_kobo=amount_kobo,
        provider_ref=provider_ref,
        state=state,
        description=description,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def record_audit_log(
    db: Session,
    action: str,
    object_type: str,
    object_id: str,
    actor_id: Optional[UUID] = None,
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None
) -> models.AuditLog:
    """
    Appends an immutable audit log entry for critical system events.
    """
    audit = models.AuditLog(
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
