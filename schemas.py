from __future__ import annotations
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from models import (
    UserRole,
    UserStatus,
    ProductCondition,
    ProductStatus,
    OrderStatus,
    PaymentStatus,
    LedgerEntryType,
    LedgerState,
    DisputeReason,
    DisputeStatus,
    DisputeResolution,
    DeliveryMethod,
)


# --- User & Auth Schemas ---

class UserRegister(BaseModel):
    email: EmailStr
    matric_no: Optional[str] = Field(None, description="e.g. 2020/1/12345EE for FUT Minna")
    phone: Optional[str] = Field(None, description="Contact phone number")
    password: str = Field(..., min_length=6)
    full_name: str
    school_name: str = "FUT Minna"
    role: UserRole = UserRole.BUYER


class UserLogin(BaseModel):
    username: str = Field(..., description="Email or Matric Number")
    password: str


class VerifyMatricRequest(BaseModel):
    matric_no: str
    school_name: str = "FUT Minna"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    refresh_token: str
    user_id: UUID
    role: UserRole
    email: str
    full_name: str
    model_config = {"from_attributes": True}


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    device_label: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    matric_no: Optional[str] = None
    phone: Optional[str] = None
    full_name: str
    profile_photo_url: Optional[str] = None
    school_name: str
    location: Optional[str] = None
    role: UserRole
    status: UserStatus
    is_verified: bool
    verified_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    profile_photo_url: Optional[str] = None
    location: Optional[str] = None


# --- Vendor Schemas ---

class VendorRegister(BaseModel):
    store_name: str
    store_description: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None


class VendorOut(BaseModel):
    id: UUID
    user_id: UUID
    store_name: str
    store_description: Optional[str] = None
    verification_level: int
    payout_account_ref: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class VendorUpdate(BaseModel):
    store_name: Optional[str] = None
    store_description: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None


# --- Address Schemas ---

class AddressCreate(BaseModel):
    title: str
    address_line: str
    city: str = "Minna"
    state: str = "Niger"
    phone: Optional[str] = None
    is_default: bool = False


class AddressOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    address_line: str
    city: str
    state: str
    phone: Optional[str] = None
    is_default: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Category Schemas ---

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[UUID] = None


class CategoryOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Product Schemas ---

class ProductImageCreate(BaseModel):
    image_url: str
    sort_order: int = 0


class ProductImageOut(BaseModel):
    id: UUID
    image_url: str
    sort_order: int
    created_at: datetime
    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    category_id: UUID
    title: str
    description: str
    condition: ProductCondition = ProductCondition.USED
    price_kobo: int = Field(..., gt=0, description="Price in kobo (e.g. 100,000 kobo = 1,000 NGN)")
    stock: int = Field(1, ge=1)
    location: Optional[str] = None
    prep_time_minutes: int = 20
    images: Optional[List[ProductImageCreate]] = None


class ProductUpdate(BaseModel):
    category_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[ProductCondition] = None
    price_kobo: Optional[int] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    status: Optional[ProductStatus] = None
    location: Optional[str] = None
    prep_time_minutes: Optional[int] = None


class ProductOut(BaseModel):
    id: UUID
    vendor_id: UUID
    category_id: UUID
    title: str
    description: str
    condition: ProductCondition
    price_kobo: int
    stock: int
    status: ProductStatus
    location: Optional[str] = None
    prep_time_minutes: int
    created_at: datetime
    updated_at: datetime
    images: List[ProductImageOut] = []
    category: Optional[CategoryOut] = None
    model_config = {"from_attributes": True}


# --- Pickup Hub Schemas ---

class PickupHubCreate(BaseModel):
    name: str
    campus: str = "FUT Minna"
    location: str
    coordinates: Optional[str] = None
    image_url: Optional[str] = None


class PickupHubOut(BaseModel):
    id: UUID
    name: str
    campus: str
    location: str
    coordinates: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Order Schemas ---

class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(1, ge=1)


class OrderItemOut(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    unit_price_kobo: int
    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    vendor_id: UUID
    hub_id: Optional[UUID] = None
    delivery_method: DeliveryMethod = DeliveryMethod.PICKUP_HUB
    items: List[OrderItemCreate]


class OrderTimelineOut(BaseModel):
    id: UUID
    from_status: Optional[str] = None
    to_status: str
    actor_id: Optional[UUID] = None
    note: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: UUID
    buyer_id: UUID
    vendor_id: UUID
    hub_id: Optional[UUID] = None
    delivery_method: DeliveryMethod
    status: OrderStatus
    gross_amount_kobo: int
    platform_fee_kobo: int
    protection_window_ends_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut] = []
    timeline: List[OrderTimelineOut] = []
    model_config = {"from_attributes": True}


class VendorRejectRequest(BaseModel):
    reason: str = Field(..., min_length=3)


# --- Delivery & OTP Schemas ---

class DeliveryOTPResponse(BaseModel):
    order_id: UUID
    otp: str
    instructions: str = "Present this OTP at the pickup hub when receiving your item. Do not share with third parties."


class DeliveryVerifyOTPRequest(BaseModel):
    otp: str
    hub_id: UUID
    terminal_info: Optional[str] = None


class DeliveryOut(BaseModel):
    id: UUID
    order_id: UUID
    hub_id: UUID
    verified_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Payment Schemas ---

class PaymentInitiateResponse(BaseModel):
    order_id: UUID
    provider: str
    provider_ref: str
    amount_kobo: int
    authorization_url: str
    access_code: Optional[str] = None


class PaymentOut(BaseModel):
    id: UUID
    order_id: UUID
    provider: str
    provider_ref: str
    amount_kobo: int
    status: PaymentStatus
    verified_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Transaction Ledger Schemas ---

class TransactionLedgerOut(BaseModel):
    id: UUID
    order_id: UUID
    type: LedgerEntryType
    amount_kobo: int
    provider_ref: Optional[str] = None
    state: LedgerState
    description: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Dispute Schemas ---

class DisputeCreate(BaseModel):
    reason: DisputeReason
    description: str
    evidence_urls: Optional[List[str]] = []


class DisputeResolveRequest(BaseModel):
    resolution: DisputeResolution
    resolution_note: str


class DisputeOut(BaseModel):
    id: UUID
    order_id: UUID
    buyer_id: UUID
    reason: DisputeReason
    description: str
    evidence_urls: Optional[List[str]] = []
    status: DisputeStatus
    resolution: DisputeResolution
    resolved_by: Optional[UUID] = None
    resolution_note: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# --- Review Schemas ---

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    id: UUID
    order_id: UUID
    reviewer_id: UUID
    reviewee_id: UUID
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Audit Log & Notification Schemas ---

class AuditLogOut(BaseModel):
    id: UUID
    actor_id: Optional[UUID] = None
    action: str
    object_type: str
    object_id: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    payload: Dict[str, Any]
    sent_at: datetime
    read_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
