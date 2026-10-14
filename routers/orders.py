from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db, settings
import models
import schemas
from services import auth, utils, state_machine, ledger

router = APIRouter(prefix="/orders", tags=["Orders & State Machine"])

@router.post("", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: schemas.OrderCreate,
    db: Session = Depends(get_db),
    buyer: models.User = Depends(auth.get_current_user)
):
    """
    Creates a new order with items.
    Generates the buyer's delivery OTP, reserves stock, and places order in PAYMENT_PENDING state.
    """
    if not order_in.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must contain at least one item")

    vendor = db.query(models.User).filter(models.User.id == order_in.vendor_id).first()
    if not vendor or vendor.role not in [models.UserRole.VENDOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    if buyer.id == vendor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot purchase from your own store")

    gross_amount_kobo = 0
    items_to_create = []

    for item_in in order_in.items:
        product = db.query(models.Product).filter(
            models.Product.id == item_in.product_id,
            models.Product.vendor_id == vendor.id,
            models.Product.status == models.ProductStatus.ACTIVE
        ).first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item_in.product_id} not available from this vendor"
            )

        if product.stock < item_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{product.title}'. Only {product.stock} available."
            )

        # Deduct stock
        product.stock -= item_in.quantity
        line_total = product.price_kobo * item_in.quantity
        gross_amount_kobo += line_total

        items_to_create.append({
            "product_id": product.id,
            "quantity": item_in.quantity,
            "unit_price_kobo": product.price_kobo
        })

    platform_fee_kobo = int(gross_amount_kobo * (settings.PLATFORM_FEE_PERCENTAGE / 100.0))

    # Create Order
    order = models.Order(
        buyer_id=buyer.id,
        vendor_id=vendor.id,
        hub_id=order_in.hub_id,
        delivery_method=order_in.delivery_method,
        status=models.OrderStatus.PAYMENT_PENDING,
        gross_amount_kobo=gross_amount_kobo,
        platform_fee_kobo=platform_fee_kobo,
    )
    db.add(order)
    db.flush()

    # Add Order Items
    for it in items_to_create:
        order_item = models.OrderItem(
            order_id=order.id,
            product_id=it["product_id"],
            quantity=it["quantity"],
            unit_price_kobo=it["unit_price_kobo"]
        )
        db.add(order_item)

    # Generate Delivery OTP and Delivery Record
    hub_id = order_in.hub_id
    if not hub_id:
        default_hub = db.query(models.PickupHub).filter(models.PickupHub.is_active == True).first()
        if default_hub:
            hub_id = default_hub.id

    if hub_id:
        raw_otp = utils.generate_otp(6)
        hashed_otp = utils.hash_otp(raw_otp)
        delivery = models.Delivery(
            order_id=order.id,
            hub_id=hub_id,
            otp_hash=hashed_otp,
            device_meta={"created_by_ip": "client", "buyer_id": str(buyer.id), "raw_otp_cache": raw_otp}
        )
        db.add(delivery)

    # Initial Timeline
    initial_timeline = models.OrderTimeline(
        order_id=order.id,
        from_status=None,
        to_status=models.OrderStatus.PAYMENT_PENDING.value,
        actor_id=buyer.id,
        note="Order created, awaiting payment authorization via Protected Checkout.",
    )
    db.add(initial_timeline)

    db.commit()
    db.refresh(order)
    return order

@router.get("/buyer", response_model=List[schemas.OrderOut])
def get_buyer_orders(
    db: Session = Depends(get_db),
    buyer: models.User = Depends(auth.get_current_user)
):
    """Lists orders placed by the current student buyer."""
    return db.query(models.Order).filter(models.Order.buyer_id == buyer.id).order_by(models.Order.created_at.desc()).all()

@router.get("/vendor", response_model=List[schemas.OrderOut])
def get_vendor_orders(
    db: Session = Depends(get_db),
    vendor: models.User = Depends(auth.require_vendor)
):
    """Lists orders received by the current vendor."""
    return db.query(models.Order).filter(models.Order.vendor_id == vendor.id).order_by(models.Order.created_at.desc()).all()

@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves order details."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if current_user.id not in [order.buyer_id, order.vendor_id] and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to view this order")

    return order

@router.get("/{order_id}/timeline", response_model=List[schemas.OrderTimelineOut])
def get_order_timeline(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves immutable audit timeline of order transitions."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if current_user.id not in [order.buyer_id, order.vendor_id] and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    return order.timeline

@router.post("/{order_id}/vendor/accept", response_model=schemas.OrderOut)
def vendor_accept_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    vendor: models.User = Depends(auth.require_vendor)
):
    """
    Vendor accepts an order within the 20-minute SLA.
    Transitions VENDOR_PENDING -> VENDOR_ACCEPTED -> PREPARING.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order or order.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Step 1: VENDOR_PENDING -> VENDOR_ACCEPTED
    state_machine.transition_order_status(
        order,
        models.OrderStatus.VENDOR_ACCEPTED,
        actor_id=vendor.id,
        db=db,
        note="Vendor accepted order within SLA window."
    )

    # Step 2: VENDOR_ACCEPTED -> PREPARING
    state_machine.transition_order_status(
        order,
        models.OrderStatus.PREPARING,
        actor_id=vendor.id,
        db=db,
        note="Vendor is preparing items for delivery."
    )

    return order

@router.post("/{order_id}/vendor/reject", response_model=schemas.OrderOut)
def vendor_reject_order(
    order_id: UUID,
    reject_req: schemas.VendorRejectRequest,
    db: Session = Depends(get_db),
    vendor: models.User = Depends(auth.require_vendor)
):
    """
    Vendor rejects an order (out of stock, cannot fulfill).
    Triggers state transition to VENDOR_REJECTED -> REFUND_PENDING and restocks items.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order or order.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Restock inventory
    for it in order.items:
        prod = db.query(models.Product).filter(models.Product.id == it.product_id).first()
        if prod:
            prod.stock += it.quantity

    # Transition to VENDOR_REJECTED
    state_machine.transition_order_status(
        order,
        models.OrderStatus.VENDOR_REJECTED,
        actor_id=vendor.id,
        db=db,
        note=f"Vendor rejected order: {reject_req.reason}"
    )

    # Transition to REFUND_PENDING
    state_machine.transition_order_status(
        order,
        models.OrderStatus.REFUND_PENDING,
        actor_id=vendor.id,
        db=db,
        note="Automated refund scheduled via Paystack API."
    )

    # Record ledger entry for refund liability
    ledger.record_ledger_entry(
        db=db,
        order_id=order.id,
        entry_type=models.LedgerEntryType.REFUND,
        amount_kobo=order.gross_amount_kobo,
        state=models.LedgerState.PENDING,
        description=f"Refund pending due to vendor rejection: {reject_req.reason}"
    )

    return order

@router.post("/{order_id}/vendor/ready", response_model=schemas.OrderOut)
def vendor_ready_for_pickup(
    order_id: UUID,
    db: Session = Depends(get_db),
    vendor: models.User = Depends(auth.require_vendor)
):
    """
    Vendor marks order ready for dropoff at pickup hub.
    Transitions PREPARING -> READY_FOR_PICKUP.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order or order.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return state_machine.transition_order_status(
        order,
        models.OrderStatus.READY_FOR_PICKUP,
        actor_id=vendor.id,
        db=db,
        note="Vendor packaged item and is en route to Pickup Hub."
    )

@router.post("/{order_id}/hub/received", response_model=schemas.OrderOut)
def hub_confirm_received(
    order_id: UUID,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """
    Hub staff/kiosk confirms item physically dropped at the pickup hub.
    Transitions READY_FOR_PICKUP -> AT_PICKUP_HUB.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return state_machine.transition_order_status(
        order,
        models.OrderStatus.AT_PICKUP_HUB,
        actor_id=admin.id,
        db=db,
        note="Item verified and logged at campus Pickup Hub."
    )
