from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import utils, auth

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new student user at FUT Minna.
    """
    # Check duplicate email
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists."
        )

    # Check duplicate matric number if provided
    if user_in.matric_no:
        if db.query(models.User).filter(models.User.matric_no == user_in.matric_no).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this matric number already exists."
            )

    # Check duplicate phone if provided
    if user_in.phone:
        if db.query(models.User).filter(models.User.phone == user_in.phone).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this phone number already exists."
            )

    user = models.User(
        email=user_in.email,
        matric_no=user_in.matric_no,
        phone=user_in.phone,
        password_hash=utils.hash_password(user_in.password),
        full_name=user_in.full_name,
        school_name=user_in.school_name,
        role=user_in.role,
        status=models.UserStatus.ACTIVE,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@router.post("/verify-matric", response_model=schemas.UserOut)
def verify_matric(
    req: schemas.VerifyMatricRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Validates a student's matriculation number at FUT Minna and activates verified status (Level 1).
    """
    matric = req.matric_no.strip().upper()
    existing = db.query(models.User).filter(models.User.matric_no == matric, models.User.id != current_user.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Matric number already registered to another account."
        )

    current_user.matric_no = matric
    current_user.school_name = req.school_name
    current_user.is_verified = True
    current_user.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)

    return current_user

@router.post("/login", response_model=schemas.TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint supporting standard OAuth2 form credentials (username=email or matric_no, password).
    Returns JWT access token and cryptographic rotating refresh token.
    """
    login_id = form_data.username.strip()
    user = db.query(models.User).filter(
        (models.User.email == login_id) | (models.User.matric_no == login_id)
    ).first()

    if not user or not utils.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != models.UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}.",
        )

    access_token_data = auth.create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    refresh_token = auth.create_refresh_token(db, user.id)

    return schemas.TokenResponse(
        access_token=access_token_data["access_token"],
        token_type="Bearer",
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role,
        email=user.email,
        full_name=user.full_name,
    )

@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(
    req: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Single-use refresh token rotation.
    Detects reuse and revokes token families if breach is suspected.
    """
    user, new_raw_refresh_token = auth.verify_and_rotate_refresh_token(
        db, req.refresh_token, device_label=req.device_label
    )
    if not user or not new_raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked refresh token. Please log in again.",
        )

    access_token_data = auth.create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})

    return schemas.TokenResponse(
        access_token=access_token_data["access_token"],
        token_type="Bearer",
        refresh_token=new_raw_refresh_token,
        user_id=user.id,
        role=user.role,
        email=user.email,
        full_name=user.full_name,
    )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    req: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Revokes the active refresh token.
    """
    auth.revoke_refresh_token(db, req.refresh_token)
    return None
