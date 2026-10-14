import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Text,
    JSON,
    Uuid,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

# --- Enums ---

class UserRole(str, enum.Enum):
    BUYER = "buyer"
    VENDOR = "vendor"
    ADMIN = "admin"

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    DELETED = "deleted"

class ProductCondition(str, enum.Enum):
    NEW = "new"
    LIKE_NEW = "like_new"
    USED = "used"
    FOR_PARTS = "for_parts"

class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"
    REMOVED = "removed"
    DRAFT = "draft"

class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_EXPIRED = "payment_expired"
    PAYMENT_VERIFIED = "payment_verified"
    VENDOR_PENDING = "vendor_pending"
    VENDOR_ACCEPTED = "vendor_accepted"
    VENDOR_REJECTED = "vendor_rejected"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    AT_PICKUP_HUB = "at_pickup_hub"
    DELIVERY_VERIFIED = "delivery_verified"
    PROTECTION_WINDOW = "protection_window"
    DISPUTE_OPEN = "dispute_open"
    UNDER_REVIEW = "under_review"
    SETTLEMENT_PENDING = "settlement_pending"
    SETTLED = "settled"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class LedgerEntryType(str, enum.Enum):
    CHARGE = "charge"
    REFUND = "refund"
    PAYOUT = "payout"
    FEE = "fee"

class LedgerState(str, enum.Enum):
    PENDING = "pending"
    COMMITTED = "committed"
    REVERSED = "reversed"

class DisputeReason(str, enum.Enum):
    ITEM_NOT_RECEIVED = "item_not_received"
    ITEM_NOT_AS_DESCRIBED = "item_not_as_described"
    DAMAGED = "damaged"
    OTHER = "other"

class DisputeStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED_BUYER = "resolved_buyer"
    RESOLVED_SELLER = "resolved_seller"
    CLOSED = "closed"

class DisputeResolution(str, enum.Enum):
    FULL_REFUND = "full_refund"
    PARTIAL_REFUND = "partial_refund"
    CASE_DISMISSED = "case_dismissed"
    NONE = "none"

class DeliveryMethod(str, enum.Enum):
    PICKUP_HUB = "pickup_hub"
    MEETUP = "meetup"
    THIRD_PARTY_LOGISTICS = "third_party_logistics"


# --- Models ---

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    matric_no = Column(String(50), unique=True, nullable=True, index=True)
    phone = Column(String(30), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    profile_photo_url = Column(String(500), nullable=True)
    school_name = Column(String(150), default="FUT Minna", nullable=False)
    location = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.BUYER, nullable=False)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    vendor_profile = relationship("VendorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="vendor")
    orders_as_buyer = relationship("Order", foreign_keys="[Order.buyer_id]", back_populates="buyer")
    orders_as_vendor = relationship("Order", foreign_keys="[Order.vendor_id]", back_populates="vendor")
    reviews_written = relationship("Review", foreign_keys="[Review.reviewer_id]", back_populates="reviewer")
    reviews_received = relationship("Review", foreign_keys="[Review.reviewee_id]", back_populates="reviewee")
    disputes_raised = relationship("Dispute", foreign_keys="[Dispute.buyer_id]", back_populates="buyer")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class VendorProfile(Base):
    __tablename__ = "vendor_profiles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    store_name = Column(String(150), nullable=False, unique=True)
    store_description = Column(Text, nullable=True)
    verification_level = Column(Integer, default=0, nullable=False)  # 0: Basic, 1: Matric/Email Verified, 2: Payout-KYC
    payout_account_ref = Column(String(100), nullable=True)  # Paystack subaccount or recipient code
    bank_name = Column(String(100), nullable=True)
    account_number = Column(String(20), nullable=True)
    account_name = Column(String(150), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="vendor_profile")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    device_label = Column(String(150), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)  # e.g., "Hostel Room", "Campus Gate"
    address_line = Column(String(255), nullable=False)
    city = Column(String(100), default="Minna", nullable=False)
    state = Column(String(100), default="Niger", nullable=False)
    phone = Column(String(30), nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="addresses")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subcategories = relationship("Category", backref="parent", remote_side=[id])
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    vendor_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    condition = Column(SQLEnum(ProductCondition), default=ProductCondition.USED, nullable=False)
    price_kobo = Column(BigInteger, nullable=False)
    stock = Column(Integer, default=1, nullable=False)
    status = Column(SQLEnum(ProductStatus), default=ProductStatus.ACTIVE, nullable=False, index=True)
    location = Column(String(200), nullable=True)
    prep_time_minutes = Column(Integer, default=20, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    vendor = relationship("User", back_populates="products")
    category = relationship("Category", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order")
    order_items = relationship("OrderItem", back_populates="product")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    product_id = Column(Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product = relationship("Product", back_populates="images")


class PickupHub(Base):
    __tablename__ = "pickup_hubs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(150), nullable=False, index=True)
    campus = Column(String(100), default="FUT Minna", nullable=False)
    location = Column(String(255), nullable=False)
    coordinates = Column(String(100), nullable=True)  # "lat,lng" or JSON
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    orders = relationship("Order", back_populates="pickup_hub")
    deliveries = relationship("Delivery", back_populates="pickup_hub")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    buyer_id = Column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    vendor_id = Column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    hub_id = Column(Uuid, ForeignKey("pickup_hubs.id", ondelete="SET NULL"), nullable=True, index=True)
    delivery_method = Column(SQLEnum(DeliveryMethod), default=DeliveryMethod.PICKUP_HUB, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.DRAFT, nullable=False, index=True)
    gross_amount_kobo = Column(BigInteger, nullable=False)
    platform_fee_kobo = Column(BigInteger, default=0, nullable=False)
    protection_window_ends_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="orders_as_buyer")
    vendor = relationship("User", foreign_keys=[vendor_id], back_populates="orders_as_vendor")
    pickup_hub = relationship("PickupHub", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    timeline = relationship("OrderTimeline", back_populates="order", cascade="all, delete-orphan", order_by="OrderTimeline.created_at")
    delivery = relationship("Delivery", back_populates="order", uselist=False, cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")
    ledger_entries = relationship("TransactionLedger", back_populates="order")
    disputes = relationship("Dispute", back_populates="order")
    reviews = relationship("Review", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(Uuid, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Uuid, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price_kobo = Column(BigInteger, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class OrderTimeline(Base):
    __tablename__ = "order_timeline"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(Uuid, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    actor_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="timeline")
    actor = relationship("User")


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(Uuid, ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    hub_id = Column(Uuid, ForeignKey("pickup_hubs.id", ondelete="RESTRICT"), nullable=False)
    otp_hash = Column(String(64), nullable=False)  # SHA-256 hash of buyer OTP
    verified_at = Column(DateTime(timezone=True), nullable=True)
    device_meta = Column(JSON, nullable=True)  # IP, User-Agent, hub terminal details
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="delivery")
    pickup_hub = relationship("PickupHub", back_populates="deliveries")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    provider = Column(String(50), default="paystack", nullable=False)
    provider_ref = Column(String(100), unique=True, nullable=False, index=True)
    amount_kobo = Column(BigInteger, nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    raw_response = Column(JSON, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order = relationship("Order", back_populates="payments")


class TransactionLedger(Base):
    """
    Append-only immutable financial ledger.
    Every financial event (charge, refund, vendor payout, platform fee) is immutably logged here.
    """
    __tablename__ = "transaction_ledger"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    type = Column(SQLEnum(LedgerEntryType), nullable=False, index=True)
    amount_kobo = Column(BigInteger, nullable=False)
    provider_ref = Column(String(100), nullable=True, index=True)
    state = Column(SQLEnum(LedgerState), default=LedgerState.COMMITTED, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    order = relationship("Order", back_populates="ledger_entries")


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    buyer_id = Column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    reason = Column(SQLEnum(DisputeReason), nullable=False)
    description = Column(Text, nullable=False)
    evidence_urls = Column(JSON, default=list, nullable=True)
    status = Column(SQLEnum(DisputeStatus), default=DisputeStatus.OPEN, nullable=False, index=True)
    resolution = Column(SQLEnum(DisputeResolution), default=DisputeResolution.NONE, nullable=False)
    resolved_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="disputes")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="disputes_raised")
    resolver = relationship("User", foreign_keys=[resolved_by])


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(Uuid, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewee_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_written")
    reviewee = relationship("User", foreign_keys=[reviewee_id], back_populates="reviews_received")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # e.g. "ORDER_ACCEPTED", "READY_FOR_PICKUP"
    payload = Column(JSON, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="notifications")


class AuditLog(Base):
    """
    Append-only immutable system audit trail for high-impact actions.
    """
    __tablename__ = "audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    actor_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., "DISPUTE_RESOLVED", "VENDOR_VERIFIED"
    object_type = Column(String(50), nullable=False, index=True)  # "ORDER", "DISPUTE", "VENDOR"
    object_id = Column(String(100), nullable=False, index=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    actor = relationship("User")
