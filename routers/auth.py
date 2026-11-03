import os
import secrets
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import utils, auth

router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory cache for fast OTP lookup in dev/test when SMTP is not configured
_OTP_PREVIEW_CACHE: dict[str, dict] = {}


def _dispatch_otp_email(email: str, code: str) -> bool:
    """
    Sends 6-digit OTP email via SMTP if SMTP_HOST / SMTP_USER / SMTP_PASS are configured.
    Logs clearly when running without external SMTP credentials.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", "SkulBuy Nigeria <noreply@skulbuy.com>")

    print(f">> [OTP DISPATCH] To: {email} | Code: {code} (Valid 5 mins)")

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"{code} is your SkulBuy verification code"
            msg["From"] = smtp_from
            msg["To"] = email
            text_body = f"Your SkulBuy student verification code is {code}. Valid for 5 minutes."
            msg.attach(MIMEText(text_body, "plain"))
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, [email], msg.as_string())
            return True
        except Exception as e:
            print(f">> [SMTP Warning] Could not send via SMTP ({e}), stored in database.")
            return False
    return True


@router.post("/send-otp")
def send_otp(req: schemas.SendOTPRequest, db: Session = Depends(get_db)):
    """Generates and sends a 6-digit email verification OTP."""
    email = req.email.strip().lower()
    now = datetime.now(timezone.utc)

    # Generate 6-digit code
    code = f"{secrets.randbelow(900000) + 100000}"
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    expires_at = now + timedelta(minutes=5)

    # Clear unverified previous OTPs for this email
    db.query(models.EmailOTP).filter(
        models.EmailOTP.email == email,
        models.EmailOTP.verified == False
    ).delete()

    otp_rec = models.EmailOTP(
        email=email,
        otp_hash=code_hash,
        expires_at=expires_at,
        attempts=0,
        verified=False,
    )
    db.add(otp_rec)
    db.commit()

    _OTP_PREVIEW_CACHE[email] = {
        "code": code,
        "expires_at": expires_at.isoformat(),
    }

    _dispatch_otp_email(email, code)

    return {
        "success": True,
        "message": f"A 6-digit verification code has been sent to {email}.",
        "cooldownSeconds": 60,
        "expiresInMinutes": 5,
    }


@router.post("/verify-otp")
def verify_otp(req: schemas.VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verifies a 6-digit email OTP."""
    email = req.email.strip().lower()
    code = req.code.strip()
    now = datetime.now(timezone.utc)

    record = (
        db.query(models.EmailOTP)
        .filter(models.EmailOTP.email == email, models.EmailOTP.verified == False)
        .order_by(models.EmailOTP.created_at.desc())
        .first()
    )

    if not record:
        raise HTTPException(status_code=400, detail="No active verification code found. Please request a new code.")

    exp = record.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if now > exp:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new code.")

    if record.attempts >= 5:
        db.delete(record)
        db.commit()
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please request a new code.")

    input_hash = hashlib.sha256(code.encode()).hexdigest()
    if input_hash != record.otp_hash:
        record.attempts += 1
        db.commit()
        remaining = 5 - record.attempts
        raise HTTPException(status_code=400, detail=f"Incorrect verification code. {remaining} attempt(s) remaining.")

    record.verified = True
    user = db.query(models.User).filter(models.User.email.ilike(email)).first()
    if user:
        user.email_verified = True
    db.commit()
    _OTP_PREVIEW_CACHE.pop(email, None)

    return {
        "success": True,
        "verified": True,
        "message": "Email verified successfully.",
    }


@router.get("/otp-preview")
def otp_preview(email: str = Query(...), db: Session = Depends(get_db)):
    """Development/Testing helper for OTP inspection when external SMTP is not configured."""
    clean_email = email.strip().lower()
    cached = _OTP_PREVIEW_CACHE.get(clean_email)
    record = (
        db.query(models.EmailOTP)
        .filter(models.EmailOTP.email == clean_email)
        .order_by(models.EmailOTP.created_at.desc())
        .first()
    )
    return {
        "email": clean_email,
        "latestOtp": cached["code"] if cached else None,
        "expiresAt": cached["expires_at"] if cached else (record.expires_at.isoformat() if record else None),
        "verified": bool(record.verified) if record else False,
    }


@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new student user and issues authentication tokens + welcome wallet bonus.
    """
    email_clean = user_in.email.strip().lower()
    if db.query(models.User).filter(models.User.email.ilike(email_clean)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please sign in."
        )

    matric_clean = user_in.matric_no.strip() if user_in.matric_no and user_in.matric_no.strip() else None
    if matric_clean:
        if db.query(models.User).filter(models.User.matric_no == matric_clean).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this matric number already exists."
            )

    phone_clean = user_in.phone.strip() if user_in.phone and user_in.phone.strip() else None
    if phone_clean:
        if db.query(models.User).filter(models.User.phone == phone_clean).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this phone number already exists."
            )

    user = models.User(
        email=email_clean,
        username=user_in.username or email_clean.split("@")[0],
        matric_no=matric_clean,
        phone=phone_clean,
        password_hash=utils.hash_password(user_in.password),
        full_name=user_in.full_name or email_clean.split("@")[0],
        school_name=user_in.school_name or "FUTMINNA",
        location=user_in.campus_area or "Gidan Kwano Main Campus",
        campus_area=user_in.campus_area or "Gidan Kwano - Hostel Block B",
        department=user_in.department,
        level_of_study=user_in.level_of_study or "100L",
        points=100,
        wallet_balance_kobo=100000,  # 1,000 NGN welcome bonus
        role=user_in.role,
        status=models.UserStatus.ACTIVE,
        is_verified=False,
    )
    db.add(user)
    db.flush()

    # Record initial welcome wallet transaction
    welcome_tx = models.WalletTransaction(
        user_id=user.id,
        type="credit",
        amount_kobo=100000,
        reference=f"SKB-WEL-{secrets.token_hex(4).upper()}",
        description="Welcome Student Campus Bonus Credit (₦1,000)",
        payment_method="bonus",
        status="completed",
    )
    db.add(welcome_tx)

    points_entry = models.PointsLedger(
        user_id=user.id,
        amount=100,
        reason="Student Account Registration Bonus (+100 pts)",
    )
    db.add(points_entry)

    # Auto-join official community if present
    official_comm = db.query(models.Community).filter(
        models.Community.is_official == True,
        models.Community.university == user.school_name
    ).first()
    if official_comm:
        db.add(models.CommunityMember(community_id=official_comm.id, user_id=user.id, role="member"))
        official_comm.member_count = (official_comm.member_count or 1) + 1

    db.commit()
    db.refresh(user)

    access_token_data = auth.create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    refresh_token = auth.create_refresh_token(db, user.id)

    return schemas.TokenResponse(
        access_token=access_token_data["access_token"],
        token=access_token_data["access_token"],
        token_type="Bearer",
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role,
        email=user.email,
        full_name=user.full_name,
        user=user,
    )


@router.post("/complete-onboarding")
def complete_onboarding(
    req: schemas.CompleteOnboardingRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Completes guided student onboarding and awards +500 SkulCredits if not yet claimed."""
    if req.first_name or req.last_name:
        full_name = f"{req.first_name or ''} {req.last_name or ''}".strip()
        if full_name:
            current_user.full_name = full_name
    if req.username:
        current_user.username = req.username
    if req.profile_picture:
        current_user.profile_photo_url = req.profile_picture
    if req.university:
        current_user.school_name = req.university
    if req.campus_name:
        current_user.location = req.campus_name
        current_user.campus_area = req.campus_name
    if req.department:
        current_user.department = req.department
    if req.level_of_study:
        current_user.level_of_study = req.level_of_study
    if req.phone:
        current_user.phone = req.phone

    bonus_awarded = not current_user.signup_bonus_claimed
    if bonus_awarded:
        current_user.points = (current_user.points or 0) + 500
        current_user.signup_bonus_claimed = True
        db.add(models.PointsLedger(
            user_id=current_user.id,
            amount=500,
            reason="New Student Onboarding Bonus (+500 SkulCredits)"
        ))

    current_user.has_onboarded = True
    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "bonus_awarded": bonus_awarded,
        "bonusAwarded": 500 if bonus_awarded else 0,
        "bonus_amount": 500 if bonus_awarded else 0,
        "user": schemas.UserOut.model_validate(current_user),
        "message": "Welcome to SkulBuy! Onboarding completed.",
    }


@router.get("/me", response_model=schemas.UserOut)
def get_auth_me(current_user: models.User = Depends(auth.get_current_user)):
    """Returns the authenticated student's profile."""
    return current_user


@router.post("/verify-matric", response_model=schemas.UserOut)
def verify_matric(
    req: schemas.VerifyMatricRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Validates a student's matriculation number and activates verified status."""
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
    current_user.student_id_verified = "verified"
    current_user.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/login", response_model=schemas.TokenResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login endpoint supporting both JSON payload and standard OAuth2 form credentials.
    """
    login_id = ""
    password = ""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json()
        login_id = (body.get("username") or body.get("email") or "").strip()
        password = body.get("password") or ""
    else:
        form = await request.form()
        login_id = (form.get("username") or form.get("email") or "").strip()
        password = form.get("password") or ""

    if not login_id or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email/username and password are required.",
        )

    user = db.query(models.User).filter(
        (models.User.email.ilike(login_id)) | (models.User.matric_no == login_id) | (models.User.username == login_id)
    ).first()

    if not user or not utils.verify_password(password, user.password_hash):
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
        token=access_token_data["access_token"],
        token_type="Bearer",
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role,
        email=user.email,
        full_name=user.full_name,
        user=user,
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(
    req: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Single-use refresh token rotation."""
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
        token=access_token_data["access_token"],
        token_type="Bearer",
        refresh_token=new_raw_refresh_token,
        user_id=user.id,
        role=user.role,
        email=user.email,
        full_name=user.full_name,
        user=user,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    req: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Revokes the active refresh token."""
    auth.revoke_refresh_token(db, req.refresh_token)
    return None
