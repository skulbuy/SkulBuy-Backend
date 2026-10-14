from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import auth

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=schemas.UserOut)
def get_my_profile(current_user: models.User = Depends(auth.get_current_user)):
    """Returns the authenticated student's profile."""
    return current_user

@router.patch("/me", response_model=schemas.UserOut)
def update_my_profile(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Updates user personal details (full_name, phone, photo, location)."""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    if user_update.profile_photo_url is not None:
        current_user.profile_photo_url = user_update.profile_photo_url
    if user_update.location is not None:
        current_user.location = user_update.location

    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user_public_profile(user_id: UUID, db: Session = Depends(get_db)):
    """Public profile of another user / student."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# --- Delivery Addresses ---

@router.post("/me/addresses", response_model=schemas.AddressOut, status_code=status.HTTP_201_CREATED)
def create_address(
    addr_in: schemas.AddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Adds a delivery address for the user."""
    if addr_in.is_default:
        db.query(models.Address).filter(models.Address.user_id == current_user.id).update({"is_default": False})

    address = models.Address(
        user_id=current_user.id,
        title=addr_in.title,
        address_line=addr_in.address_line,
        city=addr_in.city,
        state=addr_in.state,
        phone=addr_in.phone or current_user.phone,
        is_default=addr_in.is_default,
    )
    db.add(address)
    db.commit()
    db.refresh(address)
    return address

@router.get("/me/addresses", response_model=List[schemas.AddressOut])
def list_my_addresses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves all saved addresses for the authenticated user."""
    return db.query(models.Address).filter(models.Address.user_id == current_user.id).all()

@router.delete("/me/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Deletes a delivery address."""
    addr = db.query(models.Address).filter(
        models.Address.id == address_id,
        models.Address.user_id == current_user.id
    ).first()
    if not addr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    db.delete(addr)
    db.commit()
    return None
