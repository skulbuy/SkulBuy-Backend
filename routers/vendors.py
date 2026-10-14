from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import auth

router = APIRouter(prefix="/vendors", tags=["Vendors"])

@router.post("/register", response_model=schemas.VendorOut, status_code=status.HTTP_201_CREATED)
def register_vendor(
    vendor_in: schemas.VendorRegister,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Onboards an authenticated student as a vendor.
    Grants vendor role and sets Level 0/1 verification level.
    """
    existing = db.query(models.VendorProfile).filter(models.VendorProfile.user_id == current_user.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vendor profile already exists for this account."
        )

    store_conflict = db.query(models.VendorProfile).filter(models.VendorProfile.store_name == vendor_in.store_name).first()
    if store_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Store name is already taken. Please choose another."
        )

    level = 1 if current_user.is_verified else 0

    profile = models.VendorProfile(
        user_id=current_user.id,
        store_name=vendor_in.store_name,
        store_description=vendor_in.store_description,
        bank_name=vendor_in.bank_name,
        account_number=vendor_in.account_number,
        account_name=vendor_in.account_name,
        verification_level=level,
    )
    current_user.role = models.UserRole.VENDOR

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile

@router.get("/me", response_model=schemas.VendorOut)
def get_my_vendor_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_vendor)
):
    """Returns the authenticated vendor's store profile."""
    profile = db.query(models.VendorProfile).filter(models.VendorProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")
    return profile

@router.patch("/me", response_model=schemas.VendorOut)
def update_my_vendor_profile(
    update_in: schemas.VendorUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_vendor)
):
    """Updates store description and payout bank details."""
    profile = db.query(models.VendorProfile).filter(models.VendorProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")

    if update_in.store_name and update_in.store_name != profile.store_name:
        conflict = db.query(models.VendorProfile).filter(models.VendorProfile.store_name == update_in.store_name).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Store name already taken")
        profile.store_name = update_in.store_name

    if update_in.store_description is not None:
        profile.store_description = update_in.store_description
    if update_in.bank_name is not None:
        profile.bank_name = update_in.bank_name
    if update_in.account_number is not None:
        profile.account_number = update_in.account_number
    if update_in.account_name is not None:
        profile.account_name = update_in.account_name

    db.commit()
    db.refresh(profile)
    return profile

@router.get("/{vendor_id}", response_model=schemas.VendorOut)
def get_vendor_by_id(vendor_id: UUID, db: Session = Depends(get_db)):
    """Public vendor profile."""
    profile = db.query(models.VendorProfile).filter(
        (models.VendorProfile.id == vendor_id) | (models.VendorProfile.user_id == vendor_id)
    ).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return profile
