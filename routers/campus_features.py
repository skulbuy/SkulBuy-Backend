import os
import uuid
import base64
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from database import get_db, settings
import models
import schemas
from services import auth, utils

router = APIRouter(tags=["Campus Ecosystem & Features"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

NIGERIAN_UNIVERSITIES = [
    {
        "id": 1,
        "name": "Federal University of Technology, Minna",
        "short_name": "FUTMINNA",
        "city": "Minna",
        "state": "Niger State",
        "type": "Federal",
        "student_count": 28000,
        "logo_url": "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=200&q=80",
        "lat": 9.5312,
        "lng": 6.4529,
        "campuses": [
            {"name": "Gidan Kwano Main Campus", "campus_type": "Main Campus", "city": "Minna", "state": "Niger State", "lat": 9.5312, "lng": 6.4529, "description": "Hostel Blocks A-D, SEET, SAAT, SICT, SUB Complex, Library"},
            {"name": "Bosso Campus", "campus_type": "Mini Campus", "city": "Minna", "state": "Niger State", "lat": 9.6139, "lng": 6.5463, "description": "Bosso Gate, Science Quad, Halls 1 & 2"},
            {"name": "Off-Campus - Gidan Kwano Village Lodges", "campus_type": "Student Lodge Zone", "city": "Minna", "state": "Niger State", "lat": 9.5250, "lng": 6.4600, "description": "Private off-campus student lodges & apartments"},
        ],
    },
    {
        "id": 2,
        "name": "University of Lagos",
        "short_name": "UNILAG",
        "city": "Akoka, Yaba",
        "state": "Lagos State",
        "type": "Federal",
        "student_count": 55000,
        "logo_url": "https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&w=200&q=80",
        "lat": 6.5173,
        "lng": 3.3976,
        "campuses": [
            {"name": "Akoka Main Campus", "campus_type": "Main Campus", "city": "Yaba, Lagos", "state": "Lagos State", "lat": 6.5173, "lng": 3.3976, "description": "New Hall, Moremi, Jaja, Faculty of Engineering"},
            {"name": "College of Medicine (CMUL) Idi-Araba", "campus_type": "Medical Campus", "city": "Surulere, Lagos", "state": "Lagos State", "lat": 6.5204, "lng": 3.3592, "description": "LUTH Idi-Araba medical hostels"},
        ],
    },
    {
        "id": 3,
        "name": "Ahmadu Bello University, Zaria",
        "short_name": "ABU",
        "city": "Zaria",
        "state": "Kaduna State",
        "type": "Federal",
        "student_count": 50000,
        "logo_url": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?auto=format&fit=crop&w=200&q=80",
        "lat": 11.1512,
        "lng": 7.6546,
        "campuses": [
            {"name": "Samaru Main Campus", "campus_type": "Main Campus", "city": "Zaria", "state": "Kaduna State", "lat": 11.1512, "lng": 7.6546, "description": "Engineering, Sciences, Danfodio & Suleiman Hostels"},
            {"name": "Kongo Campus", "campus_type": "Mini Campus", "city": "Zaria", "state": "Kaduna State", "lat": 11.0855, "lng": 7.7190, "description": "Law, Administration & Business"},
        ],
    },
    {
        "id": 4,
        "name": "University of Abuja",
        "short_name": "UniAbuja",
        "city": "Airport Road / Gwagwalada",
        "state": "FCT Abuja",
        "type": "Federal",
        "student_count": 36000,
        "logo_url": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?auto=format&fit=crop&w=200&q=80",
        "lat": 8.9754,
        "lng": 7.1802,
        "campuses": [
            {"name": "Main Campus (Permanent Site)", "campus_type": "Main Campus", "city": "Airport Road, Abuja", "state": "FCT Abuja", "lat": 8.9754, "lng": 7.1802, "description": "Senate building, Male & Female Hostels"},
            {"name": "Mini Campus (Gwagwalada)", "campus_type": "Mini Campus", "city": "Gwagwalada", "state": "FCT Abuja", "lat": 8.9431, "lng": 7.0858, "description": "College of Health Sciences"},
        ],
    },
    {
        "id": 5,
        "name": "University of Ibadan",
        "short_name": "UI",
        "city": "Ibadan",
        "state": "Oyo State",
        "type": "Federal",
        "student_count": 38000,
        "logo_url": "https://images.unsplash.com/photo-1546410531-bb4caa6b424d?auto=format&fit=crop&w=200&q=80",
        "lat": 7.4443,
        "lng": 3.8995,
        "campuses": [
            {"name": "UI Main Campus", "campus_type": "Main Campus", "city": "Ibadan", "state": "Oyo State", "lat": 7.4443, "lng": 3.8995, "description": "Mellanby, Tedder, Indy, Zik, Queen Idia Halls"},
        ],
    },
    {
        "id": 6,
        "name": "Obafemi Awolowo University",
        "short_name": "OAU",
        "city": "Ile-Ife",
        "state": "Osun State",
        "type": "Federal",
        "student_count": 35000,
        "logo_url": "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=200&q=80",
        "lat": 7.5186,
        "lng": 4.5219,
        "campuses": [
            {"name": "Ile-Ife Main Campus", "campus_type": "Main Campus", "city": "Ile-Ife", "state": "Osun State", "lat": 7.5186, "lng": 4.5219, "description": "Angola, Mozambique, Moremi, Fajuyi Halls & SUB"},
        ],
    },
    {
        "id": 7,
        "name": "University of Ilorin",
        "short_name": "UNILORIN",
        "city": "Ilorin",
        "state": "Kwara State",
        "type": "Federal",
        "student_count": 48000,
        "logo_url": "https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&w=200&q=80",
        "lat": 8.4812,
        "lng": 4.6748,
        "campuses": [
            {"name": "Permanent Site (PS)", "campus_type": "Main Campus", "city": "Ilorin", "state": "Kwara State", "lat": 8.4812, "lng": 4.6748, "description": "Walkway, Tanke / Oke-Odo Student Axis"},
        ],
    },
    {
        "id": 8,
        "name": "Covenant University",
        "short_name": "CU",
        "city": "Ota",
        "state": "Ogun State",
        "type": "Private",
        "student_count": 12000,
        "logo_url": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?auto=format&fit=crop&w=200&q=80",
        "lat": 6.6718,
        "lng": 3.1581,
        "campuses": [
            {"name": "Canaanland Main Campus", "campus_type": "Main Campus", "city": "Ota", "state": "Ogun State", "lat": 6.6718, "lng": 3.1581, "description": "Peter, Paul, John, Joseph, Esther,Deborah Halls"},
        ],
    },
]

CAMPUS_LOCATIONS_BY_UNI = {
    "FUT Minna": [
        "Gidan Kwano Hostels", "Bosso Campus Block B", "Bosso Campus SUB",
        "Main Library Steps, Gidan Kwano", "SEET Complex Station",
        "Gidan Kwano Off-Campus Lodges", "SICT Complex", "GK Cafeteria Axis"
    ],
    "default": [
        "Main Campus SUB", "University Library Ground Floor",
        "Student Hostels Gate", "Faculty of Engineering Complex", "Off-Campus Student Lodges"
    ]
}


# ==========================================================
# 1. UNIVERSITIES, CAMPUS LOCATIONS & GEOLOCATION
# ==========================================================

@router.get("/universities")
def list_universities():
    return NIGERIAN_UNIVERSITIES


@router.get("/campus-locations")
def list_campus_locations(university: Optional[str] = Query(None)):
    if university and university in CAMPUS_LOCATIONS_BY_UNI:
        return CAMPUS_LOCATIONS_BY_UNI[university]
    return CAMPUS_LOCATIONS_BY_UNI["FUT Minna"]


@router.get("/geolocation/suggest")
def suggest_university_by_coords(
    lat: float = Query(9.535),
    lng: float = Query(6.445),
):
    if 6.3 <= lat <= 6.7 and 3.2 <= lng <= 3.6:
        return {
            "university": NIGERIAN_UNIVERSITIES[1],
            "suggested_university": "UNILAG",
            "suggested_campus": "Akoka Main Campus",
            "suggested_area": "Main Campus SUB",
            "distanceKm": 1.4,
            "confidence": "high",
        }
    return {
        "university": NIGERIAN_UNIVERSITIES[0],
        "suggested_university": "FUT Minna",
        "suggested_campus": "Gidan Kwano Main Campus",
        "suggested_area": "Gidan Kwano Hostels",
        "distanceKm": 0.8,
        "confidence": "high",
    }


# ==========================================================
# 2. FILE / IMAGE UPLOAD (CLOUDINARY CDN + LOCAL FALLBACK)
# ==========================================================

def _upload_to_cloudinary(file_or_data: Any, folder: str = "skulbuy") -> Optional[dict]:
    """Uploads file or base64 data to Cloudinary CDN if CLOUDINARY_URL is configured."""
    cloudinary_url = os.getenv("CLOUDINARY_URL") or getattr(settings, "CLOUDINARY_URL", "")
    if not cloudinary_url:
        return None

    try:
        import cloudinary
        import cloudinary.uploader

        # Explicitly configure from CLOUDINARY_URL if needed
        cloudinary.config(cloudinary_url=cloudinary_url)

        res = cloudinary.uploader.upload(
            file_or_data,
            folder=folder,
            resource_type="auto",
            transformation=[
                {"quality": "auto", "fetch_format": "auto"}
            ],
            overwrite=True
        )
        secure_url = res.get("secure_url") or res.get("url")
        public_id = res.get("public_id")
        return {"url": secure_url, "filename": public_id}
    except Exception as e:
        print(f">> Notice: Cloudinary upload attempt failed, falling back to local/data storage: {e}")
        return None


@router.post("/upload")
async def upload_file(request: Request):
    content_type_header = request.headers.get("content-type", "")
    folder = "skulbuy/uploads"

    # 1. Base64 JSON upload
    if "application/json" in content_type_header:
        body = await request.json()
        img_data = body.get("image") or body.get("file") or ""
        folder_req = body.get("folder") or body.get("type")
        if folder_req:
            folder = f"skulbuy/{folder_req}"

        if img_data.startswith("http"):
            return {"url": img_data, "filename": "external.jpg"}

        if not img_data.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

        # Attempt Cloudinary CDN upload first
        c_res = _upload_to_cloudinary(img_data, folder=folder)
        if c_res and c_res.get("url"):
            return c_res

        # Fallback to direct data URI when Cloudinary is not configured
        return {"url": img_data, "filename": f"{uuid.uuid4().hex}.jpg"}

    # 2. Multipart form-data upload
    form = await request.form()
    file = form.get("file")
    folder_req = form.get("folder") or form.get("type")
    if folder_req:
        folder = f"skulbuy/{folder_req}"

    if not file or not hasattr(file, "read"):
        raise HTTPException(status_code=400, detail="No file uploaded")

    content = await file.read()
    if len(content) > 12 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 12MB limit")

    mime = getattr(file, "content_type", None) or "image/jpeg"
    ext = (getattr(file, "filename", None) or "image.jpg").split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp", "gif"]:
        ext = "jpg"

    # Attempt Cloudinary CDN upload
    c_res = _upload_to_cloudinary(content, folder=folder)
    if c_res and c_res.get("url"):
        return c_res

    # Local storage fallback
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    if len(content) <= 1500 * 1024:
        b64 = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{mime};base64,{b64}"
        return {"url": data_url, "filename": filename}

    return {"url": f"/uploads/{filename}", "filename": filename}


# ==========================================================
# 3. WALLET & TRANSACTIONS
# ==========================================================

@router.get("/wallet/transactions")
def get_wallet_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    txs = (
        db.query(models.WalletTransaction)
        .filter(models.WalletTransaction.user_id == current_user.id)
        .order_by(models.WalletTransaction.created_at.desc())
        .limit(50)
        .all()
    )
    items = [
        {
            "id": str(t.id),
            "user_id": str(t.user_id),
            "type": t.type,
            "amount": round(t.amount_kobo / 100.0, 2),
            "description": t.description,
            "reference": t.reference,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txs
    ]
    return {"transactions": items, "wallet_balance": round((current_user.wallet_balance_kobo or 0) / 100.0, 2)}


@router.post("/wallet/fund")
def fund_wallet(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    amount_naira = float(payload.get("amount", 0))
    method = payload.get("method", "bank_transfer")
    if amount_naira < 100:
        raise HTTPException(status_code=400, detail="Minimum wallet funding amount is ₦100")

    amount_kobo = int(round(amount_naira * 100))
    ref = f"FUND-{uuid.uuid4().hex[:10].upper()}"

    current_user.wallet_balance_kobo = (current_user.wallet_balance_kobo or 0) + amount_kobo
    tx = models.WalletTransaction(
        user_id=current_user.id,
        type="credit",
        amount_kobo=amount_kobo,
        description=f"Wallet Deposit via {method.replace('_', ' ').title()}",
        reference=ref,
        status="completed",
    )
    db.add(tx)
    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "wallet_balance": round(current_user.wallet_balance_kobo / 100.0, 2),
        "reference": ref,
    }


@router.post("/wallet/pay-listing")
def pay_listing_with_wallet(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    listing_id = payload.get("listing_id")
    if not listing_id:
        raise HTTPException(status_code=400, detail="listing_id is required")

    try:
        prod_uuid = UUID(str(listing_id))
        product = db.query(models.Product).filter(models.Product.id == prod_uuid).first()
    except ValueError:
        product = db.query(models.Product).first()

    if not product:
        raise HTTPException(status_code=404, detail="Listing not found")

    if (current_user.wallet_balance_kobo or 0) < product.price_kobo:
        raise HTTPException(status_code=400, detail="Insufficient SkulBuy Wallet balance")

    current_user.wallet_balance_kobo -= product.price_kobo
    ref = f"PAY-{uuid.uuid4().hex[:10].upper()}"
    tx = models.WalletTransaction(
        user_id=current_user.id,
        type="debit",
        amount_kobo=product.price_kobo,
        description=f"Escrow Payment for {product.title}",
        reference=ref,
        status="completed",
    )
    db.add(tx)
    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "wallet_balance": round(current_user.wallet_balance_kobo / 100.0, 2),
        "reference": ref,
    }


# ==========================================================
# 4. DAILY REWARDS & STREAKS
# ==========================================================

STREAK_SCHEDULE = [
    {"day": 1, "points": 10, "cash": 0, "label": "+10 Pts"},
    {"day": 2, "points": 15, "cash": 0, "label": "+15 Pts"},
    {"day": 3, "points": 25, "cash": 50, "label": "₦50 + 25 Pts"},
    {"day": 4, "points": 30, "cash": 0, "label": "+30 Pts"},
    {"day": 5, "points": 40, "cash": 100, "label": "₦100 + 40 Pts"},
    {"day": 6, "points": 50, "cash": 0, "label": "+50 Pts"},
    {"day": 7, "points": 100, "cash": 250, "label": "₦250 + 100 Pts"},
]


@router.get("/daily-rewards/status")
def get_daily_rewards_status(
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_user),
):
    if not current_user:
        return {
            "claimed_today": False,
            "current_streak": 0,
            "longest_streak": 0,
            "next_day": 1,
            "next_reward": STREAK_SCHEDULE[0],
            "schedule": STREAK_SCHEDULE,
            "wallet_balance": 0,
            "points": 0,
        }

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    claimed_today = current_user.last_reward_date == today_str
    streak = current_user.daily_streak or 0
    if not claimed_today and current_user.last_reward_date != yesterday_str and current_user.last_reward_date is not None:
        streak = 0

    next_day = ((streak % 7) + 1) if not claimed_today else (((streak - 1) % 7) + 1)
    next_reward = STREAK_SCHEDULE[next_day - 1]

    return {
        "claimed_today": claimed_today,
        "current_streak": streak,
        "longest_streak": current_user.longest_streak or 0,
        "next_day": next_day,
        "next_reward": next_reward,
        "schedule": STREAK_SCHEDULE,
        "wallet_balance": round((current_user.wallet_balance_kobo or 0) / 100.0, 2),
        "points": current_user.points or 0,
    }


@router.post("/daily-rewards/claim")
def claim_daily_reward(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    if current_user.last_reward_date == today_str:
        raise HTTPException(status_code=400, detail="Daily reward already claimed today")

    if current_user.last_reward_date == yesterday_str:
        new_streak = (current_user.daily_streak or 0) + 1
    else:
        new_streak = 1

    day_idx = ((new_streak - 1) % 7)
    reward_cfg = STREAK_SCHEDULE[day_idx]

    pts = reward_cfg["points"]
    cash_naira = reward_cfg["cash"]
    cash_kobo = cash_naira * 100

    current_user.daily_streak = new_streak
    current_user.longest_streak = max(current_user.longest_streak or 0, new_streak)
    current_user.last_reward_date = today_str
    current_user.points = (current_user.points or 0) + pts
    current_user.wallet_balance_kobo = (current_user.wallet_balance_kobo or 0) + cash_kobo

    reward_rec = models.DailyReward(
        user_id=current_user.id,
        claim_date=today_str,
        day_number=reward_cfg["day"],
        reward_type="combo" if cash_kobo > 0 else "points",
        points_earned=pts,
        cash_earned_kobo=cash_kobo,
    )
    db.add(reward_rec)

    pt_entry = models.PointsLedger(
        user_id=current_user.id,
        action="daily_check_in",
        points=pts,
        description=f"Day {new_streak} Campus Streak Check-in",
    )
    db.add(pt_entry)

    if cash_kobo > 0:
        tx = models.WalletTransaction(
            user_id=current_user.id,
            type="credit",
            amount_kobo=cash_kobo,
            description=f"Day {new_streak} Streak Cash Bonus",
            reference=f"STREAK-{today_str}-{str(current_user.id)[:6]}",
            status="completed",
        )
        db.add(tx)

    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "streak": new_streak,
        "reward": reward_cfg,
        "wallet_balance": round((current_user.wallet_balance_kobo or 0) / 100.0, 2),
        "points": current_user.points or 0,
    }


# ==========================================================
# 5. SAVED LISTINGS, REPORTS & VERIFICATION
# ==========================================================

@router.get("/saved", response_model=List[schemas.ProductOut])
def get_saved_listings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    saved_rows = (
        db.query(models.SavedListing)
        .filter(models.SavedListing.user_id == current_user.id)
        .order_by(models.SavedListing.created_at.desc())
        .all()
    )
    product_ids = [s.product_id for s in saved_rows]
    if not product_ids:
        return []
    return db.query(models.Product).filter(models.Product.id.in_(product_ids)).all()


@router.post("/saved/{listing_id}")
def toggle_saved_listing(
    listing_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = (
        db.query(models.SavedListing)
        .filter(
            models.SavedListing.user_id == current_user.id,
            models.SavedListing.product_id == listing_id,
        )
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        return {"saved": False}

    new_saved = models.SavedListing(user_id=current_user.id, product_id=listing_id)
    db.add(new_saved)
    db.commit()
    return {"saved": True}


@router.post("/reports")
def submit_report(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    listing_id = payload.get("listing_id")
    reason = payload.get("reason", "Policy violation")
    details = payload.get("details", "")

    prod_uuid = None
    if listing_id:
        try:
            prod_uuid = UUID(str(listing_id))
        except ValueError:
            pass

    rep = models.Report(
        reporter_id=current_user.id,
        product_id=prod_uuid,
        reason=reason,
        details=details,
        status="pending",
    )
    db.add(rep)
    db.commit()
    return {"success": True, "report_id": str(rep.id)}


@router.post("/verification/submit")
def submit_student_verification(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    matric = payload.get("matric_number") or payload.get("matric_no")
    dept = payload.get("department")
    id_card_img = payload.get("id_card_image")
    if matric:
        current_user.matric_no = matric
    if dept:
        current_user.department = dept
    if id_card_img:
        current_user.id_card_image = id_card_img

    current_user.is_verified = True
    current_user.student_id_verified = 1
    current_user.points = (current_user.points or 0) + 50
    db.add(
        models.PointsLedger(
            user_id=current_user.id,
            action="student_id_verified",
            points=50,
            description="Student ID Verification Bonus",
        )
    )
    db.commit()
    db.refresh(current_user)
    return {"success": True, "user": schemas.UserOut.model_validate(current_user)}


# ==========================================================
# 6. COMMUNITIES (CAMPUS CHAT HUBS)
# ==========================================================

def _serialize_community(c: models.Community, db: Session, current_user: Optional[models.User] = None) -> dict:
    member_count = db.query(models.CommunityMember).filter(models.CommunityMember.community_id == c.id).count()
    is_member = False
    member_role = None
    if current_user:
        mem = (
            db.query(models.CommunityMember)
            .filter(
                models.CommunityMember.community_id == c.id,
                models.CommunityMember.user_id == current_user.id,
            )
            .first()
        )
        if mem:
            is_member = True
            member_role = mem.role

    return {
        "id": str(c.id),
        "name": c.name,
        "slug": c.slug,
        "description": c.description,
        "category": c.category,
        "university": c.university,
        "icon": c.icon,
        "banner_color": c.banner_color,
        "is_official": c.is_official,
        "member_count": max(member_count, 12),
        "is_member": is_member,
        "member_role": member_role,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/communities")
def list_communities(
    university: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_user),
):
    query = db.query(models.Community)
    if university:
        query = query.filter(or_(models.Community.university == university, models.Community.university == "All Campuses"))
    if category and category != "all":
        query = query.filter(models.Community.category == category)
    if search:
        query = query.filter(models.Community.name.ilike(f"%{search}%"))

    communities = query.order_by(models.Community.is_official.desc(), models.Community.created_at.asc()).all()
    return [_serialize_community(c, db, current_user) for c in communities]


@router.get("/communities/{community_id}")
def get_community(
    community_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_user),
):
    c = db.query(models.Community).filter(models.Community.id == community_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Community not found")

    data = _serialize_community(c, db, current_user)
    pinned = (
        db.query(models.CommunityMessage)
        .filter(models.CommunityMessage.community_id == c.id, models.CommunityMessage.is_pinned == True)
        .order_by(models.CommunityMessage.created_at.desc())
        .limit(3)
        .all()
    )
    data["pinned_messages"] = [_serialize_community_message(m, db) for m in pinned]
    return data


def _serialize_community_message(m: models.CommunityMessage, db: Session) -> dict:
    reactions_rows = (
        db.query(models.CommunityReaction)
        .filter(models.CommunityReaction.message_id == m.id)
        .all()
    )
    grouped: Dict[str, List[str]] = {}
    for r in reactions_rows:
        grouped.setdefault(r.emoji, []).append(str(r.user_id))

    reactions_list = [
        {"emoji": emoji, "count": len(uids), "users": uids}
        for emoji, uids in grouped.items()
    ]

    listing_preview = None
    if m.shared_product_id:
        prod = db.query(models.Product).filter(models.Product.id == m.shared_product_id).first()
        if prod:
            listing_preview = {
                "id": str(prod.id),
                "title": prod.title,
                "price": round(prod.price_kobo / 100.0, 2),
                "image": prod.images[0] if prod.images else None,
            }

    return {
        "id": str(m.id),
        "community_id": str(m.community_id),
        "user_id": str(m.user_id),
        "user_name": m.user.full_name if m.user else "Campus Student",
        "user_username": m.user.username if m.user else None,
        "user_verified": bool(m.user.is_verified) if m.user else False,
        "user_role": m.user.role.value if (m.user and m.user.role) else "buyer",
        "user_department": m.user.department if m.user else None,
        "content": m.content,
        "message_type": m.message_type or "text",
        "shared_listing_id": str(m.shared_product_id) if m.shared_product_id else None,
        "listing_preview": listing_preview,
        "reply_to_id": str(m.reply_to_id) if m.reply_to_id else None,
        "is_pinned": bool(m.is_pinned),
        "reactions": reactions_list,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/communities/{community_id}/messages")
def get_community_messages(
    community_id: UUID,
    db: Session = Depends(get_db),
):
    msgs = (
        db.query(models.CommunityMessage)
        .filter(models.CommunityMessage.community_id == community_id)
        .order_by(models.CommunityMessage.created_at.asc())
        .limit(100)
        .all()
    )
    return [_serialize_community_message(m, db) for m in msgs]


@router.post("/communities/{community_id}/messages")
def post_community_message(
    community_id: UUID,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    content = (payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    # Ensure user is member
    mem = (
        db.query(models.CommunityMember)
        .filter(
            models.CommunityMember.community_id == community_id,
            models.CommunityMember.user_id == current_user.id,
        )
        .first()
    )
    if not mem:
        db.add(models.CommunityMember(community_id=community_id, user_id=current_user.id, role="member"))

    shared_listing_id = payload.get("shared_listing_id")
    shared_prod_uuid = None
    if shared_listing_id:
        try:
            shared_prod_uuid = UUID(str(shared_listing_id))
        except ValueError:
            pass

    reply_to_id = payload.get("reply_to_id")
    reply_uuid = None
    if reply_to_id:
        try:
            reply_uuid = UUID(str(reply_to_id))
        except ValueError:
            pass

    msg = models.CommunityMessage(
        community_id=community_id,
        user_id=current_user.id,
        content=content,
        message_type=payload.get("message_type", "text"),
        shared_product_id=shared_prod_uuid,
        reply_to_id=reply_uuid,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return _serialize_community_message(msg, db)


@router.post("/communities/{community_id}/messages/{message_id}/react")
def react_to_community_message(
    community_id: UUID,
    message_id: UUID,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    emoji = payload.get("emoji", "👍")
    existing = (
        db.query(models.CommunityReaction)
        .filter(
            models.CommunityReaction.message_id == message_id,
            models.CommunityReaction.user_id == current_user.id,
            models.CommunityReaction.emoji == emoji,
        )
        .first()
    )
    if existing:
        db.delete(existing)
    else:
        db.add(models.CommunityReaction(message_id=message_id, user_id=current_user.id, emoji=emoji))
    db.commit()
    return {"success": True}


@router.post("/communities/{community_id}/join")
def join_community(
    community_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = (
        db.query(models.CommunityMember)
        .filter(
            models.CommunityMember.community_id == community_id,
            models.CommunityMember.user_id == current_user.id,
        )
        .first()
    )
    if not existing:
        db.add(models.CommunityMember(community_id=community_id, user_id=current_user.id, role="member"))
        db.commit()
    return {"success": True, "is_member": True}


@router.post("/communities/{community_id}/leave")
def leave_community(
    community_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = (
        db.query(models.CommunityMember)
        .filter(
            models.CommunityMember.community_id == community_id,
            models.CommunityMember.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
    return {"success": True, "is_member": False}


@router.post("/communities/{community_id}/report")
def report_community_content(
    community_id: UUID,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    rep = models.Report(
        reporter_id=current_user.id,
        reason=payload.get("reason", "Community content report"),
        details=f"Community {community_id}: {payload.get('details', '')}",
        status="pending",
    )
    db.add(rep)
    db.commit()
    return {"success": True}


# ==========================================================
# 7. DIRECT BUYER-SELLER CHATS & PRICE OFFERS
# ==========================================================

def _serialize_chat(c: models.Chat, db: Session) -> dict:
    last_msg = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.chat_id == c.id)
        .order_by(models.ChatMessage.created_at.desc())
        .first()
    )
    prod = c.product
    prod_img = prod.images[0] if (prod and prod.images) else None

    return {
        "id": str(c.id),
        "listing_id": str(c.product_id) if c.product_id else None,
        "listing_title": prod.title if prod else "Campus Listing",
        "listing_price": round(prod.price_kobo / 100.0, 2) if prod else 0,
        "listing_image": prod_img,
        "buyer_id": str(c.buyer_id),
        "buyer_name": c.buyer.full_name if c.buyer else "Buyer",
        "seller_id": str(c.seller_id),
        "seller_name": c.seller.full_name if c.seller else "Seller",
        "seller_verified": bool(c.seller.is_verified) if c.seller else False,
        "last_message": last_msg.text if last_msg else "Chat started",
        "updated_at": (last_msg.created_at if last_msg else c.created_at).isoformat(),
    }


@router.get("/chats")
def list_user_chats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    chats = (
        db.query(models.Chat)
        .filter(or_(models.Chat.buyer_id == current_user.id, models.Chat.seller_id == current_user.id))
        .order_by(models.Chat.updated_at.desc())
        .all()
    )
    return [_serialize_chat(c, db) for c in chats]


@router.post("/chats/start")
def start_or_get_chat(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    listing_id = payload.get("listing_id")
    if not listing_id:
        raise HTTPException(status_code=400, detail="listing_id is required")

    try:
        prod_uuid = UUID(str(listing_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid listing_id")

    product = db.query(models.Product).filter(models.Product.id == prod_uuid).first()
    if not product:
        raise HTTPException(status_code=404, detail="Listing not found")

    if product.vendor_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot start a buyer chat on your own listing")

    existing = (
        db.query(models.Chat)
        .filter(
            models.Chat.product_id == product.id,
            models.Chat.buyer_id == current_user.id,
            models.Chat.seller_id == product.vendor_id,
        )
        .first()
    )
    if existing:
        return _serialize_chat(existing, db)

    new_chat = models.Chat(
        product_id=product.id,
        buyer_id=current_user.id,
        seller_id=product.vendor_id,
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return _serialize_chat(new_chat, db)


@router.get("/chats/{chat_id}/messages")
def get_chat_messages(
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat thread not found")

    msgs = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.chat_id == chat.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    return {
        "chat": _serialize_chat(chat, db),
        "messages": [
            {
                "id": str(m.id),
                "chat_id": str(m.chat_id),
                "sender_id": str(m.sender_id),
                "sender_name": m.sender.full_name if m.sender else "Student",
                "text": m.text,
                "offer_amount": round(m.offer_amount_kobo / 100.0, 2) if m.offer_amount_kobo else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


@router.post("/chats/{chat_id}/messages")
def send_chat_message(
    chat_id: UUID,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat thread not found")

    text_val = (payload.get("text") or "").strip()
    offer_amount = payload.get("offer_amount")
    offer_kobo = int(round(float(offer_amount) * 100)) if offer_amount else None

    if not text_val and offer_kobo:
        text_val = f"Offered ₦{float(offer_amount):,.0f} for this item"

    if not text_val:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    msg = models.ChatMessage(
        chat_id=chat.id,
        sender_id=current_user.id,
        text=text_val,
        offer_amount_kobo=offer_kobo,
    )
    chat.updated_at = datetime.now(timezone.utc)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "id": str(msg.id),
        "chat_id": str(msg.chat_id),
        "sender_id": str(msg.sender_id),
        "sender_name": current_user.full_name,
        "text": msg.text,
        "offer_amount": round(msg.offer_amount_kobo / 100.0, 2) if msg.offer_amount_kobo else None,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


@router.get("/messages/unread-summary")
def get_unread_messages_summary(
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_user),
):
    if not current_user:
        return {"privateChats": 0, "communities": 0, "direct_chats_count": 0, "community_count": 0, "total": 0}

    chat_count = (
        db.query(models.Chat)
        .filter(or_(models.Chat.buyer_id == current_user.id, models.Chat.seller_id == current_user.id))
        .count()
    )
    comm_count = (
        db.query(models.CommunityMember)
        .filter(models.CommunityMember.user_id == current_user.id)
        .count()
    )
    return {
        "privateChats": chat_count,
        "communities": comm_count,
        "direct_chats_count": chat_count,
        "community_count": comm_count,
        "total": chat_count,
    }


# ==========================================================
# 8. CAMPUS MEETUPS & EVENTS
# ==========================================================

def _serialize_meetup(m: models.Meetup, db: Session, current_user: Optional[models.User] = None) -> dict:
    attendees = db.query(models.MeetupAttendee).filter(models.MeetupAttendee.meetup_id == m.id).all()
    is_attending = False
    if current_user:
        is_attending = any(a.user_id == current_user.id for a in attendees)

    return {
        "id": str(m.id),
        "title": m.title,
        "description": m.description,
        "category": m.category,
        "university": m.university,
        "university_code": "FUTMX" if "Minna" in (m.university or "") else (m.university or "FUTMX"),
        "campus": m.campus,
        "location_name": m.location_name,
        "venue_name": m.location_name,
        "event_date": m.event_date,
        "meetup_date": f"{m.event_date} • {m.event_time}",
        "event_time": m.event_time,
        "organizer_id": str(m.organizer_id) if m.organizer_id else None,
        "organizer_name": m.organizer.full_name if m.organizer else "SkulBuy Campus Team",
        "organizer_verified": bool(m.organizer.is_verified) if m.organizer else True,
        "organizer_role": m.organizer.role.value if (m.organizer and m.organizer.role) else "ambassador",
        "organizer_department": m.organizer.department if m.organizer else "Student Union",
        "max_attendees": m.max_attendees,
        "attendee_count": max(len(attendees), 18),
        "attendees_count": max(len(attendees), 18),
        "is_attending": is_attending,
        "user_rsvp": is_attending,
        "is_featured": bool(m.is_featured),
        "banner_image": m.banner_image,
        "image_url": m.banner_image,
        "status": m.status,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "attendees": [
            {
                "id": str(a.user.id),
                "name": a.user.full_name,
                "username": a.user.username,
                "department": a.user.department,
                "level_of_study": a.user.level_of_study,
                "student_id_verified": a.user.student_id_verified,
                "rsvp_status": a.status,
            }
            for a in attendees
            if a.user
        ],
    }


@router.get("/meetups")
def list_meetups(
    university: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_user),
):
    query = db.query(models.Meetup)
    if university:
        query = query.filter(models.Meetup.university == university)
    if category and category != "all":
        query = query.filter(models.Meetup.category == category)
    if search:
        query = query.filter(models.Meetup.title.ilike(f"%{search}%"))

    meetups = query.order_by(models.Meetup.is_featured.desc(), models.Meetup.created_at.desc()).all()
    return [_serialize_meetup(m, db, current_user) for m in meetups]


@router.post("/meetups", status_code=status.HTTP_201_CREATED)
def create_meetup(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    meetup = models.Meetup(
        title=payload.get("title", "Campus Meetup"),
        description=payload.get("description", ""),
        category=payload.get("category", "networking"),
        university=payload.get("university") or current_user.school_name or "FUT Minna",
        campus=payload.get("campus") or current_user.campus or "Gidan Kwano Campus",
        location_name=payload.get("location_name", "Campus Hub"),
        event_date=payload.get("event_date", "2026-11-20"),
        event_time=payload.get("event_time", "16:00"),
        organizer_id=current_user.id,
        max_attendees=int(payload.get("max_attendees", 100)),
        banner_image=payload.get("banner_image") or "https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800&auto=format&fit=crop&q=80",
    )
    db.add(meetup)
    db.flush()
    db.add(models.MeetupAttendee(meetup_id=meetup.id, user_id=current_user.id, status="going"))
    db.commit()
    db.refresh(meetup)
    return _serialize_meetup(meetup, db, current_user)


@router.get("/meetups/{meetup_id}")
def get_meetup_detail(
    meetup_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_user),
):
    m = db.query(models.Meetup).filter(models.Meetup.id == meetup_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Meetup not found")
    return _serialize_meetup(m, db, current_user)


@router.post("/meetups/{meetup_id}/rsvp")
def rsvp_meetup(
    meetup_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = (
        db.query(models.MeetupAttendee)
        .filter(
            models.MeetupAttendee.meetup_id == meetup_id,
            models.MeetupAttendee.user_id == current_user.id,
        )
        .first()
    )
    if not existing:
        db.add(models.MeetupAttendee(meetup_id=meetup_id, user_id=current_user.id, status="going"))
        db.commit()
    return {"success": True, "is_attending": True}


@router.post("/meetups/{meetup_id}/unrsvp")
def unrsvp_meetup(
    meetup_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = (
        db.query(models.MeetupAttendee)
        .filter(
            models.MeetupAttendee.meetup_id == meetup_id,
            models.MeetupAttendee.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
    return {"success": True, "is_attending": False}


# ==========================================================
# 9. SKULBOX (COLLECTIVE STUDENT GROCERY SAVINGS)
# ==========================================================

SKULBOX_TIERS = [
    {
        "id": "starter_pack",
        "name": "Hostel Starter Pack",
        "target_amount": 15000,
        "retail_value": 19500,
        "items": ["1 Carton Indomie Super Pack", "1kg Golden Penny Semovita", "900g Peak Milk Refill", "1L Devon King's Oil", "2 Packs Cabin Biscuits"],
    },
    {
        "id": "semester_pro",
        "name": "Semester Survival Box",
        "target_amount": 30000,
        "retail_value": 39000,
        "items": ["10kg Mama Gold Rice", "2 Cartons Indomie", "5kg Garri Ijebu", "2L Vegetable Oil", "1 Carton Spaghetti", "Milo & Milk Combo Pack"],
    },
    {
        "id": "bulk_squad",
        "name": "Roommate Mega Crate",
        "target_amount": 55000,
        "retail_value": 72000,
        "items": ["25kg Royal Stallion Rice", "3 Cartons Noodles", "10kg Beans (Oloyin)", "5L Vegetable Oil", "Full crate of Eggs (x2)", "Assorted Hostel Provisions"],
    },
]


def _serialize_cycle(c: models.SkulBoxCycle, db: Session) -> dict:
    sub_count = db.query(models.SkulBoxSubscription).filter(models.SkulBoxSubscription.cycle_id == c.id).count()
    return {
        "id": str(c.id),
        "name": c.title,
        "title": c.title,
        "cycle_month": c.season_tag,
        "season_tag": c.season_tag,
        "university": c.university,
        "start_date": c.start_date,
        "lock_date": c.lock_date,
        "delivery_date": c.delivery_date,
        "pickup_location": c.pickup_location,
        "status": c.status,
        "discount_pct": c.discount_pct,
        "max_slots": c.max_slots,
        "filled_slots": max(sub_count, 18),
        "tiers": SKULBOX_TIERS,
    }


@router.get("/skulbox/cycles")
def list_skulbox_cycles(
    university: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    cycles = db.query(models.SkulBoxCycle).order_by(models.SkulBoxCycle.created_at.desc()).all()
    return [_serialize_cycle(c, db) for c in cycles]


@router.get("/skulbox/active-cycle")
def get_active_skulbox_cycle(
    university: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    cycle = db.query(models.SkulBoxCycle).filter(models.SkulBoxCycle.status == "open").first()
    if not cycle:
        cycle = db.query(models.SkulBoxCycle).first()
    if not cycle:
        return None
    return _serialize_cycle(cycle, db)


@router.get("/skulbox/my-subscriptions")
def get_my_skulbox_subscriptions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    subs = (
        db.query(models.SkulBoxSubscription)
        .filter(models.SkulBoxSubscription.user_id == current_user.id)
        .order_by(models.SkulBoxSubscription.created_at.desc())
        .all()
    )
    out = []
    for s in subs:
        contribs = (
            db.query(models.SkulBoxContribution)
            .filter(models.SkulBoxContribution.subscription_id == s.id)
            .order_by(models.SkulBoxContribution.created_at.desc())
            .all()
        )
        out.append({
            "id": str(s.id),
            "cycle_id": str(s.cycle_id),
            "cycle_title": s.cycle.title if s.cycle else "Semester SkulBox Cycle",
            "cycle_name": s.cycle.title if s.cycle else "Semester SkulBox Cycle",
            "delivery_date": s.cycle.delivery_date if s.cycle else "End of Semester",
            "pickup_location": s.cycle.pickup_location if s.cycle else "Bosso / GK SUB Hub",
            "tier_id": s.tier_id,
            "tier_name": s.tier_name,
            "package_name": s.tier_name,
            "target_amount": round(s.target_amount_kobo / 100.0, 2),
            "total_amount": round(s.target_amount_kobo / 100.0, 2),
            "paid_amount": round(s.paid_amount_kobo / 100.0, 2),
            "payment_plan": s.payment_plan,
            "redemption_pin": s.redemption_pin,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "contributions": [
                {
                    "id": str(c.id),
                    "amount": round(c.amount_kobo / 100.0, 2),
                    "payment_method": c.payment_method,
                    "reference": c.reference,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in contribs
            ],
        })
    return out


@router.post("/skulbox/subscribe")
def subscribe_to_skulbox(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    cycle_id = payload.get("cycle_id")
    tier_id = payload.get("tier_id") or payload.get("package_type") or "25k"
    payment_plan = payload.get("payment_plan", "daily")
    initial_deposit = float(payload.get("initial_deposit") or payload.get("initial_payment") or 0)
    payment_method = payload.get("payment_method", "bank_transfer")

    if tier_id == "50k":
        tier = {"id": "50k", "name": "Premium Student Box", "target_amount": 50000}
    elif tier_id == "25k":
        tier = {"id": "25k", "name": "Standard Student Box", "target_amount": 25000}
    else:
        tier = next((t for t in SKULBOX_TIERS if t["id"] == tier_id), SKULBOX_TIERS[0])

    target_kobo = tier["target_amount"] * 100
    deposit_kobo = int(round(initial_deposit * 100))

    if payment_method == "wallet" and deposit_kobo > 0:
        if (current_user.wallet_balance_kobo or 0) < deposit_kobo:
            raise HTTPException(status_code=400, detail="Insufficient SkulBuy Wallet balance for initial deposit")
        current_user.wallet_balance_kobo -= deposit_kobo
        db.add(
            models.WalletTransaction(
                user_id=current_user.id,
                type="debit",
                amount_kobo=deposit_kobo,
                description=f"SkulBox Deposit ({tier['name']})",
                reference=f"SBOX-{uuid.uuid4().hex[:8].upper()}",
                status="completed",
            )
        )

    cycle = None
    if cycle_id:
        try:
            cycle = db.query(models.SkulBoxCycle).filter(models.SkulBoxCycle.id == UUID(str(cycle_id))).first()
        except ValueError:
            pass
    if not cycle:
        cycle = db.query(models.SkulBoxCycle).first()

    sub = models.SkulBoxSubscription(
        cycle_id=cycle.id,
        user_id=current_user.id,
        tier_id=tier["id"],
        tier_name=tier["name"],
        target_amount_kobo=target_kobo,
        paid_amount_kobo=deposit_kobo,
        payment_plan=payment_plan,
        redemption_pin=utils.generate_otp(6) if deposit_kobo >= target_kobo else None,
        status="completed" if deposit_kobo >= target_kobo else "active",
    )
    db.add(sub)
    db.flush()

    if deposit_kobo > 0:
        db.add(
            models.SkulBoxContribution(
                subscription_id=sub.id,
                user_id=current_user.id,
                amount_kobo=deposit_kobo,
                payment_method=payment_method,
                reference=f"SBX-{uuid.uuid4().hex[:8].upper()}",
            )
        )

    db.commit()
    return {"success": True, "subscription_id": str(sub.id)}


@router.post("/skulbox/contribute")
def contribute_to_skulbox(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    sub_id = payload.get("subscription_id")
    amount_naira = float(payload.get("amount", 0))
    payment_method = payload.get("payment_method", "wallet")

    if amount_naira <= 0:
        raise HTTPException(status_code=400, detail="Contribution amount must be greater than 0")

    sub = (
        db.query(models.SkulBoxSubscription)
        .filter(
            models.SkulBoxSubscription.id == UUID(str(sub_id)),
            models.SkulBoxSubscription.user_id == current_user.id,
        )
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    amount_kobo = int(round(amount_naira * 100))
    if payment_method == "wallet":
        if (current_user.wallet_balance_kobo or 0) < amount_kobo:
            raise HTTPException(status_code=400, detail="Insufficient SkulBuy Wallet balance")
        current_user.wallet_balance_kobo -= amount_kobo
        db.add(
            models.WalletTransaction(
                user_id=current_user.id,
                type="debit",
                amount_kobo=amount_kobo,
                description=f"SkulBox Top-up ({sub.tier_name})",
                reference=f"SBOX-{uuid.uuid4().hex[:8].upper()}",
                status="completed",
            )
        )

    sub.paid_amount_kobo += amount_kobo
    if sub.paid_amount_kobo >= sub.target_amount_kobo:
        sub.status = "completed"
        if not sub.redemption_pin:
            sub.redemption_pin = utils.generate_otp(6)

    db.add(
        models.SkulBoxContribution(
            subscription_id=sub.id,
            user_id=current_user.id,
            amount_kobo=amount_kobo,
            payment_method=payment_method,
            reference=f"SBX-{uuid.uuid4().hex[:8].upper()}",
        )
    )
    db.commit()
    return {"success": True, "paid_amount": round(sub.paid_amount_kobo / 100.0, 2), "status": sub.status}


# ==========================================================
# 10. SKULLY AI CAMPUS ASSISTANT
# ==========================================================

@router.post("/skully/chat")
async def skully_ai_chat(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_user),
):
    user_message = (payload.get("message") or "").strip()
    university = payload.get("university") or (current_user.school_name if current_user else "FUT Minna")

    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")

    # Query live PostgreSQL products for grounded recommendations
    products = (
        db.query(models.Product)
        .filter(models.Product.status == models.ProductStatus.ACTIVE)
        .order_by(models.Product.created_at.desc())
        .limit(12)
        .all()
    )

    msg_lower = user_message.lower()
    matched_products = [
        p for p in products
        if any(tok in (p.title.lower() + " " + p.description.lower() + " " + p.category_name.lower()) for tok in msg_lower.split() if len(tok) >= 3)
    ]
    recommended = (matched_products or products)[:3]

    recommended_listings = [
        {
            "id": str(p.id),
            "title": p.title,
            "price": round(p.price_kobo / 100.0, 2),
            "condition": p.condition.value if hasattr(p.condition, "value") else str(p.condition),
            "campus_location": p.location or "Campus Hub",
            "seller_name": p.seller_name,
            "seller_verified": p.seller_verified,
            "image": p.images[0] if p.images else None,
            "image_url": p.images[0] if p.images else None,
            "images": p.images,
        }
        for p in recommended
    ]

    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_api_key:
        try:
            catalog_summary = "\n".join(
                [f"- {p.title}: ₦{p.price_kobo/100:,.0f} ({p.condition.value}) at {p.location}" for p in products[:10]]
            )
            system_prompt = (
                f"You are Skully, the official campus marketplace assistant for {university} on SkulBuy. "
                f"Keep answers concise, friendly, and grounded in student life and escrow safety (4-digit Handover PIN). "
                f"Live marketplace inventory:\n{catalog_summary}"
            )
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}",
                    json={
                        "contents": [{"parts": [{"text": f"{system_prompt}\n\nStudent asks: {user_message}"}]}]
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    reply_text = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    if reply_text:
                        return {
                            "reply": reply_text,
                            "recommended_listings": recommended_listings,
                            "recommendations": {"listings": recommended_listings, "meetups": []},
                        }
        except Exception:
            pass

    # Deterministic database-grounded response when GEMINI_API_KEY is not configured
    if "escrow" in msg_lower or "safe" in msg_lower or "pin" in msg_lower:
        reply = (
            "On SkulBuy, every checkout is protected by our **Campus Escrow & 4-Digit Handover PIN**:\n\n"
            "1. When you pay via Wallet, Bank Transfer, or Card, your funds are locked safely in Escrow.\n"
            "2. You receive a secret **4-digit Handover PIN**.\n"
            "3. Meet the seller at a verified Campus Hub (e.g., Bosso SUB or Gidan Kwano Library) and inspect the item.\n"
            "4. Only share your 4-digit PIN once you're satisfied!"
        )
    elif matched_products:
        items_str = "\n".join([f"• **{p.title}** — ₦{p.price_kobo/100:,.0f} ({p.location})" for p in recommended])
        reply = f"I found {len(matched_products)} live listing(s) on **{university}** matching your request:\n\n{items_str}\n\nTap any card below to inspect or buy with Escrow protection!"
    else:
        items_str = "\n".join([f"• **{p.title}** — ₦{p.price_kobo/100:,.0f} ({p.location})" for p in recommended])
        reply = (
            f"Here are the top verified listings currently active on **{university}**:\n\n{items_str}\n\n"
            "All items are backed by SkulBuy Escrow protection. Ask me about laptops, textbooks, hostel appliances, or campus safety!"
        )

    return {
        "reply": reply,
        "recommended_listings": recommended_listings,
        "recommendations": {"listings": recommended_listings, "meetups": []},
    }
