from uuid import UUID
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body, status
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
    """Updates user personal details."""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    if user_update.profile_photo_url is not None:
        current_user.profile_photo_url = user_update.profile_photo_url
    elif user_update.profile_picture is not None:
        current_user.profile_photo_url = user_update.profile_picture
    if user_update.location is not None:
        current_user.location = user_update.location
    if user_update.campus_area is not None:
        current_user.campus_area = user_update.campus_area
        current_user.location = user_update.campus_area
    if user_update.department is not None:
        current_user.department = user_update.department
    if user_update.matric_no is not None:
        current_user.matric_no = user_update.matric_no
    if user_update.university is not None:
        current_user.school_name = user_update.university
    elif user_update.campus is not None:
        current_user.school_name = user_update.campus
    if user_update.level_of_study is not None:
        current_user.level_of_study = user_update.level_of_study

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/profile")
def get_full_user_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Returns full profile bundle (user, listings, points_history, notifications) for ProfilePage."""
    products = (
        db.query(models.Product)
        .filter(models.Product.vendor_id == current_user.id)
        .order_by(models.Product.created_at.desc())
        .all()
    )
    points_history = (
        db.query(models.PointsLedger)
        .filter(models.PointsLedger.user_id == current_user.id)
        .order_by(models.PointsLedger.created_at.desc())
        .limit(25)
        .all()
    )
    notifications = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == current_user.id)
        .order_by(models.Notification.sent_at.desc())
        .limit(20)
        .all()
    )

    return {
        "user": schemas.UserOut.model_validate(current_user),
        "listings": [schemas.ProductOut.model_validate(p) for p in products],
        "points_history": [
            {
                "id": str(pt.id),
                "user_id": str(pt.user_id),
                "amount": pt.amount,
                "reason": pt.reason,
                "created_at": pt.created_at.isoformat(),
            }
            for pt in points_history
        ],
        "notifications": [
            {
                "id": str(n.id),
                "title": n.payload.get("title", n.type) if isinstance(n.payload, dict) else n.type,
                "message": n.payload.get("message", "") if isinstance(n.payload, dict) else str(n.payload),
                "type": n.type,
                "is_read": n.read_at is not None,
                "created_at": n.sent_at.isoformat(),
            }
            for n in notifications
        ],
    }


@router.patch("/profile")
def patch_full_user_profile(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Updates user profile and returns { user, message }."""
    updated = update_my_profile(user_update, db, current_user)
    return {
        "user": schemas.UserOut.model_validate(updated),
        "message": "Profile updated successfully.",
    }


@router.post("/upload-id-card")
def upload_id_card(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Stores student ID card reference and sets verification status to pending."""
    file_data = payload.get("fileData") or payload.get("id_card_image")
    if not file_data:
        raise HTTPException(status_code=400, detail="Identification document payload is required.")

    current_user.id_card_image = file_data[:490] if not file_data.startswith("data:") else "uploaded_student_id_card"
    current_user.student_id_verified = "pending"
    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "status": "pending",
        "message": "Student ID uploaded securely. Under review by campus moderators.",
    }


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
