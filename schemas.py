from __future__ import annotations
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, computed_field, model_validator
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
    password: str = Field("Password123!", min_length=4)
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    school_name: str = "FUTMINNA"
    university: Optional[str] = None
    campus: Optional[str] = None
    campus_area: Optional[str] = None
    department: Optional[str] = None
    level_of_study: Optional[str] = "100L"
    role: Any = UserRole.BUYER

    @model_validator(mode="before")
    @classmethod
    def normalize_register(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if not values.get("full_name"):
                fn = values.get("first_name") or ""
                ln = values.get("last_name") or ""
                combined = f"{fn} {ln}".strip()
                values["full_name"] = combined or str(values.get("email", "Student")).split("@")[0]
            if values.get("university") or values.get("campus"):
                values["school_name"] = values.get("university") or values.get("campus") or "FUTMINNA"
            role_str = str(values.get("role") or "buyer").lower()
            if role_str in ["seller", "vendor"]:
                values["role"] = UserRole.VENDOR
            elif role_str == "admin":
                values["role"] = UserRole.ADMIN
            elif role_str == "ambassador":
                values["role"] = UserRole.AMBASSADOR
            else:
                values["role"] = UserRole.BUYER
        return values


class UserLogin(BaseModel):
    username: Optional[str] = Field(None, description="Email or Matric Number")
    email: Optional[str] = Field(None, description="Email address")
    password: str


class VerifyMatricRequest(BaseModel):
    matric_no: str
    school_name: str = "FUT Minna"


class SendOTPRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str


class CompleteOnboardingRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    profile_picture: Optional[str] = None
    university: Optional[str] = None
    campus_name: Optional[str] = None
    department: Optional[str] = None
    level_of_study: Optional[str] = None
    phone: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token: Optional[str] = None
    token_type: str = "Bearer"
    refresh_token: str
    user_id: UUID
    role: UserRole
    email: str
    full_name: str
    user: Optional[UserOut] = None
    model_config = {"from_attributes": True}


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    device_label: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    username: Optional[str] = None
    matric_no: Optional[str] = None
    phone: Optional[str] = None
    full_name: str
    profile_photo_url: Optional[str] = None
    school_name: str
    location: Optional[str] = None
    department: Optional[str] = None
    level_of_study: Optional[str] = "100L"
    campus_area: Optional[str] = None
    student_id_verified: str = "not_verified"
    id_card_image: Optional[str] = None
    points: int = 100
    wallet_balance_kobo: int = 0
    daily_streak: int = 0
    longest_streak: int = 0
    last_reward_date: Optional[str] = None
    signup_bonus_claimed: bool = False
    has_onboarded: bool = False
    email_verified: bool = False
    role: UserRole
    status: UserStatus
    is_verified: bool
    verified_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}

    @computed_field
    @property
    def campus(self) -> str:
        return self.school_name or "FUTMINNA"

    @computed_field
    @property
    def university(self) -> str:
        return self.school_name or "FUTMINNA"

    @computed_field
    @property
    def campus_name(self) -> str:
        return self.location or "Gidan Kwano Main Campus"

    @computed_field
    @property
    def profile_picture(self) -> Optional[str]:
        return self.profile_photo_url

    @computed_field
    @property
    def wallet_balance(self) -> float:
        return round((self.wallet_balance_kobo or 0) / 100.0, 2)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    profile_photo_url: Optional[str] = None
    profile_picture: Optional[str] = None
    location: Optional[str] = None
    campus_area: Optional[str] = None
    department: Optional[str] = None
    matric_no: Optional[str] = None
    university: Optional[str] = None
    campus: Optional[str] = None
    level_of_study: Optional[str] = None


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

    @computed_field
    @property
    def slug(self) -> str:
        return self.name.lower().replace(" & ", "-").replace(" ", "-")


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
    category_id: Any
    title: str
    description: str
    condition: ProductCondition = ProductCondition.USED
    price_kobo: Optional[int] = Field(None, gt=0, description="Price in kobo")
    price: Optional[float] = None
    stock: int = Field(1, ge=1)
    location: Optional[str] = None
    campus_location: Optional[str] = None
    university: Optional[str] = "FUTMINNA"
    is_negotiable: bool = True
    is_rental: bool = False
    rental_period: Optional[str] = "per day"
    prep_time_minutes: int = 20
    image_url: Optional[str] = None
    images: Optional[List[ProductImageCreate]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_product_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # 1. Normalize price / price_kobo
            if values.get("price_kobo") is None and values.get("price") is not None:
                try:
                    values["price_kobo"] = int(round(float(values["price"]) * 100))
                except (ValueError, TypeError):
                    values["price_kobo"] = 100000
            elif values.get("price_kobo") is None:
                values["price_kobo"] = 100000

            # 2. Normalize condition
            cond = str(values.get("condition") or "").lower()
            if "new" in cond and "fairly" not in cond and "like" not in cond:
                values["condition"] = ProductCondition.NEW
            elif "like" in cond:
                values["condition"] = ProductCondition.LIKE_NEW
            else:
                values["condition"] = ProductCondition.USED

            # 3. Normalize location
            if not values.get("location") and values.get("campus_location"):
                values["location"] = values.get("campus_location")

            # 4. Normalize images
            imgs = values.get("images")
            if isinstance(imgs, list):
                norm_imgs = []
                for i, img in enumerate(imgs):
                    if isinstance(img, str):
                        norm_imgs.append({"image_url": img, "sort_order": i})
                    elif isinstance(img, dict):
                        norm_imgs.append(img)
                values["images"] = norm_imgs
            elif values.get("image_url"):
                values["images"] = [{"image_url": values["image_url"], "sort_order": 0}]

        return values


class ProductUpdate(BaseModel):
    category_id: Optional[Any] = None
    title: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[Any] = None
    price_kobo: Optional[int] = Field(None, gt=0)
    price: Optional[float] = None
    stock: Optional[int] = Field(None, ge=0)
    status: Optional[Any] = None
    location: Optional[str] = None
    campus_location: Optional[str] = None
    is_negotiable: Optional[bool] = None
    is_rental: Optional[bool] = None
    rental_period: Optional[str] = None
    image_url: Optional[str] = None
    images: Optional[Any] = None
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
    university: Optional[str] = "FUTMINNA"
    is_negotiable: bool = True
    is_boosted: bool = False
    is_rental: bool = False
    rental_period: Optional[str] = "per day"
    views: int = 0
    prep_time_minutes: int = 20
    created_at: datetime
    updated_at: datetime
    image_objects: List[ProductImageOut] = Field(default=[], validation_alias="images")
    category: Optional[CategoryOut] = None
    vendor: Optional[UserOut] = None
    model_config = {"from_attributes": True, "populate_by_name": True}

    @computed_field
    @property
    def price(self) -> float:
        return round(self.price_kobo / 100.0, 2)

    @computed_field
    @property
    def image_url(self) -> str:
        if self.image_objects and len(self.image_objects) > 0:
            return self.image_objects[0].image_url
        return "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=600&auto=format&fit=crop&q=80"

    @computed_field
    @property
    def images(self) -> List[str]:
        if self.image_objects and len(self.image_objects) > 0:
            return [img.image_url for img in self.image_objects]
        return [self.image_url]

    @computed_field
    @property
    def seller_id(self) -> str:
        return str(self.vendor_id)

    @computed_field
    @property
    def seller_name(self) -> str:
        if self.vendor and self.vendor.full_name:
            return self.vendor.full_name
        return "Verified Student Seller"

    @computed_field
    @property
    def seller_verified(self) -> str:
        if self.vendor and (self.vendor.is_verified or self.vendor.student_id_verified == "verified"):
            return "verified"
        return "verified"

    @computed_field
    @property
    def seller_department(self) -> str:
        if self.vendor and self.vendor.department:
            return self.vendor.department
        return "FUT Minna Student"

    @computed_field
    @property
    def seller_area(self) -> str:
        if self.vendor and self.vendor.campus_area:
            return self.vendor.campus_area
        return self.location or "Gidan Kwano Campus"

    @computed_field
    @property
    def category_name(self) -> str:
        if self.category and self.category.name:
            return self.category.name
        return "Campus Marketplace"

    @computed_field
    @property
    def category_slug(self) -> str:
        if self.category:
            return self.category.slug
        return "campus-marketplace"

    @computed_field
    @property
    def campus(self) -> str:
        return self.university or "FUTMINNA"

    @computed_field
    @property
    def campus_location(self) -> str:
        return self.location or "Gidan Kwano Campus"


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


class CheckoutRequest(BaseModel):
    listing_id: Any
    quantity: int = 1
    fulfilment_type: str = "pickup"
    fulfilment_address: Optional[str] = None
    buyer_phone: Optional[str] = None
    buyer_notes: Optional[str] = None
    payment_method: str = "wallet"


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
    hub_id: Optional[UUID] = None
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
