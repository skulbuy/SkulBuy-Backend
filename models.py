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
    SELLER = "seller"
    AMBASSADOR = "ambassador"
    ADMIN = "admin"

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    DELETED = "deleted"

class ProductCondition(str, enum.Enum):
    NEW = "new"
    BRAND_NEW = "new"
    LIKE_NEW = "like_new"
    USED = "used"
    FOR_PARTS = "for_parts"

class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"
    REMOVED = "removed"
    WITHDRAWN = "withdrawn"
    SUSPENDED = "suspended"
    DRAFT = "draft"

class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_EXPIRED = "payment_expired"
    PAYMENT_VERIFIED = "payment_verified"
    PAID = "payment_verified"
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
    DOORSTEP_DELIVERY = "third_party_logistics"


# --- Core Models ---

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True, index=True)
    matric_no = Column(String(50), unique=True, nullable=True, index=True)
    phone = Column(String(30), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    profile_photo_url = Column(String(500), nullable=True)
    school_name = Column(String(150), default="FUTMINNA", nullable=False)
    location = Column(String(255), nullable=True)
    department = Column(String(150), nullable=True)
    level_of_study = Column(String(50), default="100L", nullable=True)
    campus_area = Column(String(255), nullable=True)
    student_id_verified = Column(String(50), default="not_verified", nullable=False)  # not_verified, pending, verified, rejected
    id_card_image = Column(String(500), nullable=True)
    points = Column(Integer, default=100, nullable=False)
    wallet_balance_kobo = Column(BigInteger, default=0, nullable=False)
    daily_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_reward_date = Column(String(20), nullable=True)
    signup_bonus_claimed = Column(Boolean, default=False, nullable=False)
    has_onboarded = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
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
    wallet_transactions = relationship("WalletTransaction", back_populates="user", cascade="all, delete-orphan")
    points_ledger = relationship("PointsLedger", back_populates="user", cascade="all, delete-orphan")


class VendorProfile(Base):
    __tablename__ = "vendor_profiles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    store_name = Column(String(150), nullable=False, unique=True)
    store_description = Column(Text, nullable=True)
    verification_level = Column(Integer, default=0, nullable=False)
    payout_account_ref = Column(String(100), nullable=True)
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


class EmailOTP(Base):
    __tablename__ = "email_otps"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
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
    university = Column(String(100), default="FUTMINNA", nullable=True, index=True)
    is_negotiable = Column(Boolean, default=True, nullable=False)
    is_boosted = Column(Boolean, default=False, nullable=False)
    is_rental = Column(Boolean, default=False, nullable=False)
    rental_period = Column(String(50), default="per day", nullable=True)
    views = Column(Integer, default=0, nullable=False)
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


class SavedListing(Base):
    __tablename__ = "saved_listings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    product = relationship("Product")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    reporter_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Uuid, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    reason = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, reviewed, action_taken, dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reporter = relationship("User")
    product = relationship("Product")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(30), nullable=False)  # credit, debit
    amount_kobo = Column(BigInteger, nullable=False)
    reference = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    payment_method = Column(String(50), default="wallet", nullable=False)
    status = Column(String(50), default="completed", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="wallet_transactions")


class University(Base):
    __tablename__ = "universities"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(50), unique=True, nullable=False, index=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    type = Column(String(50), default="Federal", nullable=False)
    student_count = Column(Integer, default=25000, nullable=False)
    logo_url = Column(String(500), nullable=True)
    lat = Column(Float, default=9.5312, nullable=True)
    lng = Column(Float, default=6.4529, nullable=True)
    campuses_json = Column(JSON, default=list, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PointsLedger(Base):
    __tablename__ = "points_ledger"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Integer, default=0, nullable=False)
    points = Column(Integer, default=0, nullable=True)
    action = Column(String(100), nullable=True)
    reason = Column(String(255), default="Campus Activity Reward", nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="points_ledger")


class DailyReward(Base):
    __tablename__ = "daily_rewards"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reward_date = Column(String(20), nullable=True, index=True)  # YYYY-MM-DD
    claim_date = Column(String(20), nullable=True, index=True)
    day_number = Column(Integer, default=1, nullable=True)
    reward_type = Column(String(30), default="points", nullable=True)
    points_earned = Column(Integer, default=10, nullable=True)
    cash_earned_kobo = Column(BigInteger, default=0, nullable=True)
    amount_kobo = Column(BigInteger, default=1000, nullable=False)
    streak_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    product_id = Column(Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    last_message = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product = relationship("Product")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    chat_id = Column(Uuid, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    offer_amount_kobo = Column(BigInteger, nullable=True)
    offer_status = Column(String(30), default="none", nullable=False)
    attachment_url = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User")


class Community(Base):
    __tablename__ = "communities"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(150), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="campus_life", nullable=False)
    university = Column(String(100), default="FUTMINNA", nullable=False)
    icon = Column(String(50), default="🎓", nullable=True)
    banner_color = Column(String(100), default="from-amber-600 to-orange-600", nullable=True)
    image_url = Column(String(500), nullable=True)
    is_official = Column(Boolean, default=True, nullable=False)
    member_count = Column(Integer, default=1, nullable=False)
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CommunityMember(Base):
    __tablename__ = "community_members"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    community_id = Column(Uuid, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(30), default="member", nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CommunityMessage(Base):
    __tablename__ = "community_messages"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    community_id = Column(Uuid, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text", nullable=True)
    shared_product_id = Column(Uuid, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    reply_to_id = Column(String(100), nullable=True)
    reply_to_sender = Column(String(150), nullable=True)
    reply_to_content = Column(Text, nullable=True)
    is_pinned = Column(Boolean, default=False, nullable=False)
    is_announcement = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sender = relationship("User", foreign_keys=[user_id])
    user = relationship("User", foreign_keys=[user_id], overlaps="sender")


class CommunityReaction(Base):
    __tablename__ = "community_reactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    message_id = Column(Uuid, ForeignKey("community_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reaction = Column(String(30), default="❤️", nullable=False)
    emoji = Column(String(30), default="❤️", nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Meetup(Base):
    __tablename__ = "meetups"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    university = Column(String(100), nullable=False, index=True)
    campus = Column(String(150), nullable=True)
    campus_name = Column(String(150), nullable=True)
    location = Column(String(255), default="Campus Hub", nullable=False)
    location_name = Column(String(255), nullable=True)
    date_time = Column(String(100), default="Upcoming", nullable=False)
    event_date = Column(String(50), nullable=True)
    event_time = Column(String(50), nullable=True)
    image_url = Column(String(500), nullable=True)
    banner_image = Column(String(500), nullable=True)
    organizer_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    organizer_name = Column(String(150), default="SkulBuy Campus Team", nullable=False)
    organizer_role = Column(String(100), default="Student Lead", nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    max_participants = Column(Integer, default=100, nullable=False)
    max_attendees = Column(Integer, default=100, nullable=True)
    status = Column(String(50), default="upcoming", nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organizer = relationship("User", foreign_keys=[organizer_id])


class MeetupAttendee(Base):
    __tablename__ = "meetup_attendees"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    meetup_id = Column(Uuid, ForeignKey("meetups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), default="going", nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])


class SkulBoxCycle(Base):
    __tablename__ = "skulbox_cycles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(150), default="Semester SkulBox Cycle", nullable=False)
    title = Column(String(150), nullable=True)
    cycle_month = Column(String(100), default="Active Batch", nullable=False)
    season_tag = Column(String(100), nullable=True)
    university = Column(String(100), default="FUTMINNA", nullable=True)
    start_date = Column(String(50), nullable=True)
    close_date = Column(String(100), default="25th of the Month", nullable=False)
    lock_date = Column(String(50), nullable=True)
    delivery_window = Column(String(150), default="1st Week of Month", nullable=False)
    delivery_date = Column(String(50), nullable=True)
    pickup_location = Column(String(200), default="Campus SUB Hub", nullable=True)
    status = Column(String(50), default="open", nullable=False)
    discount_pct = Column(Integer, default=25, nullable=True)
    max_slots = Column(Integer, default=250, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SkulBoxSubscription(Base):
    __tablename__ = "skulbox_subscriptions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle_id = Column(Uuid, ForeignKey("skulbox_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    package_type = Column(String(50), default="25k", nullable=False)
    tier_id = Column(String(50), nullable=True)
    package_name = Column(String(150), default="Standard Student Box", nullable=False)
    tier_name = Column(String(150), nullable=True)
    total_amount_kobo = Column(BigInteger, default=2500000, nullable=False)
    target_amount_kobo = Column(BigInteger, nullable=True)
    paid_amount_kobo = Column(BigInteger, default=0, nullable=False)
    payment_plan = Column(String(50), default="daily", nullable=False)
    redemption_pin = Column(String(20), nullable=True)
    status = Column(String(50), default="active", nullable=False)
    delivery_location = Column(String(255), default="Gidan Kwano Campus", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cycle = relationship("SkulBoxCycle")
    contributions = relationship("SkulBoxContribution", back_populates="subscription", cascade="all, delete-orphan")


class SkulBoxContribution(Base):
    __tablename__ = "skulbox_contributions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    subscription_id = Column(Uuid, ForeignKey("skulbox_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_kobo = Column(BigInteger, nullable=False)
    payment_method = Column(String(50), nullable=False)
    payment_reference = Column(String(100), default="SBX-REF", nullable=False)
    reference = Column(String(100), nullable=True)
    status = Column(String(50), default="confirmed", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subscription = relationship("SkulBoxSubscription", back_populates="contributions")


class PickupHub(Base):
    __tablename__ = "pickup_hubs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(150), nullable=False, index=True)
    campus = Column(String(100), default="FUT Minna", nullable=False)
    location = Column(String(255), nullable=False)
    coordinates = Column(String(100), nullable=True)
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
    hub_id = Column(Uuid, ForeignKey("pickup_hubs.id", ondelete="RESTRICT"), nullable=True)
    otp_hash = Column(String(64), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    device_meta = Column(JSON, nullable=True)
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
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_written")
    reviewee = relationship("User", foreign_keys=[reviewee_id], back_populates="reviews_received")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    actor_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    object_type = Column(String(50), nullable=False, index=True)
    object_id = Column(String(100), nullable=False, index=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    actor = relationship("User")
