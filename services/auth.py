import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db, settings
import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

ALGORITHM = settings.ALGORITHM
KEY = settings.KEY
EXPIRE_MINUTES = settings.EXPIRE
REFRESH_EXPIRE_DAYS = settings.REFRESH_EXPIRE_DAYS

def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()

def create_access_token(data: dict) -> dict:
    """
    Creates a signed short-lived JWT access token with an explicit 'type': 'access' claim.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, KEY, algorithm=ALGORITHM)
    return {"access_token": encoded_jwt, "type": "Bearer"}

def create_refresh_token(db: Session, user_id, device_label: Optional[str] = None) -> str:
    """
    Generates an opaque cryptographic refresh token, stores its SHA-256 hash in DB,
    and returns the raw token to the client.
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)

    record = models.RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_label=device_label,
    )
    db.add(record)
    db.commit()

    return raw_token

def verify_and_rotate_refresh_token(db: Session, raw_token: str, device_label: Optional[str] = None):
    """
    Validates a refresh token and ROTATES it: old token is marked revoked and a new one is issued.
    If an already revoked token is used, all active refresh tokens for that user are revoked.
    """
    token_hash = _hash_token(raw_token)
    record = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == token_hash
    ).first()

    if not record:
        return None, None

    now = datetime.now(timezone.utc)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if record.revoked_at is not None:
        # Compromise detection: revoke all active tokens for this user
        db.query(models.RefreshToken).filter(
            models.RefreshToken.user_id == record.user_id,
            models.RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": now})
        db.commit()
        return None, None

    if now > expires_at:
        return None, None

    # Rotate: revoke current and issue new
    record.revoked_at = now
    db.commit()

    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    if not user:
        return None, None

    new_raw_token = create_refresh_token(db, user.id, device_label=device_label)
    return user, new_raw_token

def revoke_refresh_token(db: Session, raw_token: str):
    """Marks a refresh token as revoked upon logout."""
    token_hash = _hash_token(raw_token)
    record = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == token_hash
    ).first()
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        db.commit()

def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, key=KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = verify_access_token(token, credentials_exception)
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise credentials_exception

    if user.status in [models.UserStatus.SUSPENDED, models.UserStatus.BANNED, models.UserStatus.DELETED]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}",
        )

    return user

def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user

def require_vendor(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role not in [models.UserRole.VENDOR, models.UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor access required",
        )
    return user
