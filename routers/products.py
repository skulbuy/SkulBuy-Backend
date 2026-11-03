from uuid import UUID
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import auth

router = APIRouter(prefix="/products", tags=["Products & Marketplace"])


@router.get("", response_model=List[schemas.ProductOut])
def list_products(
    q: Optional[str] = Query(None, description="Search keyword in title or description"),
    search: Optional[str] = Query(None, description="Search keyword alias"),
    category: Optional[str] = Query(None, description="Category name, slug, or UUID"),
    category_id: Optional[UUID] = Query(None, description="Filter by category UUID"),
    condition: Optional[str] = Query(None, description="Filter by condition"),
    location: Optional[str] = Query(None, description="Filter by campus location"),
    min_price_kobo: Optional[int] = Query(None, ge=0, description="Minimum price in kobo"),
    max_price_kobo: Optional[int] = Query(None, ge=0, description="Maximum price in kobo"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price in Naira"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price in Naira"),
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor"),
    university: Optional[str] = Query(None, description="University filter"),
    scope: Optional[str] = Query(None, description="Scope (e.g. campus, trending, trending_other)"),
    is_rental: Optional[str] = Query(None, description="Rental filter"),
    sort: Optional[str] = Query(None, description="Sort order (newest, price_asc, price_desc, views)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Search and browse marketplace products."""
    query = db.query(models.Product).filter(models.Product.status == models.ProductStatus.ACTIVE)

    search_term = q or search
    if search_term:
        search_pattern = f"%{search_term.strip()}%"
        query = query.filter(
            (models.Product.title.ilike(search_pattern)) |
            (models.Product.description.ilike(search_pattern))
        )

    if category_id:
        query = query.filter(models.Product.category_id == category_id)
    elif category:
        try:
            cat_uuid = UUID(str(category))
            query = query.filter(models.Product.category_id == cat_uuid)
        except (ValueError, TypeError):
            clean_cat = str(category).replace("-", " ")
            query = query.join(models.Product.category).filter(
                models.Category.name.ilike(f"%{clean_cat}%")
            )

    if condition:
        cond_lower = condition.strip().lower()
        if "new" in cond_lower and "fairly" not in cond_lower and "like" not in cond_lower:
            query = query.filter(models.Product.condition == models.ProductCondition.NEW)
        elif "like" in cond_lower:
            query = query.filter(models.Product.condition == models.ProductCondition.LIKE_NEW)
        elif "used" in cond_lower:
            query = query.filter(models.Product.condition == models.ProductCondition.USED)

    if location:
        query = query.filter(models.Product.location.ilike(f"%{location.strip()}%"))

    if is_rental is not None and is_rental != "":
        want_rental = str(is_rental).lower() in ["1", "true", "yes"]
        query = query.filter(models.Product.is_rental == want_rental)

    if min_price_kobo is not None:
        query = query.filter(models.Product.price_kobo >= min_price_kobo)
    elif min_price is not None:
        query = query.filter(models.Product.price_kobo >= int(min_price * 100))

    if max_price_kobo is not None:
        query = query.filter(models.Product.price_kobo <= max_price_kobo)
    elif max_price is not None:
        query = query.filter(models.Product.price_kobo <= int(max_price * 100))

    if vendor_id:
        query = query.filter(models.Product.vendor_id == vendor_id)

    if sort == "price_asc":
        query = query.order_by(models.Product.price_kobo.asc())
    elif sort == "price_desc":
        query = query.order_by(models.Product.price_kobo.desc())
    elif sort == "views" or scope == "trending":
        query = query.order_by(models.Product.views.desc(), models.Product.created_at.desc())
    else:
        query = query.order_by(models.Product.created_at.desc())

    return query.offset(offset).limit(limit).all()


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """Retrieves single product details and increments view count."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.views = (product.views or 0) + 1
    db.commit()
    db.refresh(product)
    return product


@router.post("", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    prod_in: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Creates a new product listing and awards +25 SkulBox points."""
    category = None
    try:
        cat_uuid = UUID(str(prod_in.category_id))
        category = db.query(models.Category).filter(models.Category.id == cat_uuid).first()
    except (ValueError, TypeError, AttributeError):
        pass

    if not category and prod_in.category_id:
        clean_name = str(prod_in.category_id).replace("-", " ")
        category = db.query(models.Category).filter(models.Category.name.ilike(f"%{clean_name}%")).first()

    if not category:
        category = db.query(models.Category).first()
        if not category:
            category = models.Category(name="General Campus Marketplace")
            db.add(category)
            db.commit()
            db.refresh(category)

    if not current_user.vendor_profile:
        store_name = f"{current_user.full_name}'s Campus Store"
        existing_store = db.query(models.VendorProfile).filter(models.VendorProfile.store_name == store_name).first()
        if existing_store:
            store_name = f"{current_user.full_name} ({str(current_user.id)[:4]})"
        vendor_prof = models.VendorProfile(
            user_id=current_user.id,
            store_name=store_name,
            store_description="Student seller on SkulBuy",
        )
        db.add(vendor_prof)
        db.commit()

    product = models.Product(
        vendor_id=current_user.id,
        category_id=category.id,
        title=prod_in.title,
        description=prod_in.description,
        condition=prod_in.condition,
        price_kobo=prod_in.price_kobo,
        stock=prod_in.stock,
        status=models.ProductStatus.ACTIVE,
        location=prod_in.location or prod_in.campus_location or current_user.location or "Gidan Kwano Campus",
        university=prod_in.university or current_user.school_name or "FUTMINNA",
        is_negotiable=prod_in.is_negotiable,
        is_rental=prod_in.is_rental,
        rental_period=prod_in.rental_period or "per day",
        prep_time_minutes=prod_in.prep_time_minutes,
    )
    db.add(product)
    db.flush()

    if prod_in.images:
        for idx, img in enumerate(prod_in.images):
            image_record = models.ProductImage(
                product_id=product.id,
                image_url=img.image_url,
                sort_order=img.sort_order if img.sort_order else idx,
            )
            db.add(image_record)

    # Award +25 SkulBox points for publishing a listing
    current_user.points = (current_user.points or 0) + 25
    db.add(models.PointsLedger(
        user_id=current_user.id,
        amount=25,
        reason=f"Posted item: {prod_in.title[:35]}"
    ))

    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: UUID,
    prod_in: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Updates product attributes and images (Owner vendor or Admin)."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.vendor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this product")

    if prod_in.category_id is not None:
        try:
            cat_uuid = UUID(str(prod_in.category_id))
            cat = db.query(models.Category).filter(models.Category.id == cat_uuid).first()
            if cat:
                product.category_id = cat.id
        except (ValueError, TypeError):
            pass

    if prod_in.title is not None:
        product.title = prod_in.title
    if prod_in.description is not None:
        product.description = prod_in.description
    if prod_in.condition is not None:
        cond_str = str(prod_in.condition).lower()
        if "new" in cond_str and "fairly" not in cond_str and "like" not in cond_str:
            product.condition = models.ProductCondition.NEW
        elif "like" in cond_str:
            product.condition = models.ProductCondition.LIKE_NEW
        else:
            product.condition = models.ProductCondition.USED
    if prod_in.price_kobo is not None:
        product.price_kobo = prod_in.price_kobo
    elif prod_in.price is not None:
        product.price_kobo = int(round(float(prod_in.price) * 100))
    if prod_in.stock is not None:
        product.stock = prod_in.stock
    if prod_in.status is not None:
        st_str = str(prod_in.status).lower()
        if st_str in [e.value for e in models.ProductStatus]:
            product.status = models.ProductStatus(st_str)
    if prod_in.location is not None or prod_in.campus_location is not None:
        product.location = prod_in.location or prod_in.campus_location
    if prod_in.is_negotiable is not None:
        product.is_negotiable = prod_in.is_negotiable
    if prod_in.is_rental is not None:
        product.is_rental = prod_in.is_rental
    if prod_in.rental_period is not None:
        product.rental_period = prod_in.rental_period
    if prod_in.prep_time_minutes is not None:
        product.prep_time_minutes = prod_in.prep_time_minutes

    # Replace images if passed
    if prod_in.images and isinstance(prod_in.images, list):
        db.query(models.ProductImage).filter(models.ProductImage.product_id == product.id).delete()
        for idx, img in enumerate(prod_in.images):
            url = img if isinstance(img, str) else img.get("image_url")
            if url:
                db.add(models.ProductImage(product_id=product.id, image_url=url, sort_order=idx))
    elif prod_in.image_url:
        db.query(models.ProductImage).filter(models.ProductImage.product_id == product.id).delete()
        db.add(models.ProductImage(product_id=product.id, image_url=prod_in.image_url, sort_order=0))

    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/status")
def update_product_status(
    product_id: UUID,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Updates listing status ('active', 'sold', 'withdrawn') and awards points if sold."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Listing not found")

    if product.vendor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Unauthorized to modify this listing")

    new_status = str(payload.get("status", "active")).lower()
    if new_status == "withdrawn":
        product.status = models.ProductStatus.WITHDRAWN
    elif new_status == "sold":
        product.status = models.ProductStatus.SOLD
        current_user.points = (current_user.points or 0) + 50
        db.add(models.PointsLedger(
            user_id=current_user.id,
            amount=50,
            reason="Item marked as sold on campus (+50 pts)"
        ))
    else:
        product.status = models.ProductStatus.ACTIVE

    db.commit()
    return {"success": True, "status": new_status}


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Marks a product as REMOVED (soft delete)."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.vendor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this product")

    product.status = models.ProductStatus.REMOVED
    db.commit()
    return None


@router.post("/{product_id}/images", response_model=schemas.ProductImageOut, status_code=status.HTTP_201_CREATED)
def add_product_image(
    product_id: UUID,
    img_in: schemas.ProductImageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Adds a photo to a product."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.vendor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this product")

    image = models.ProductImage(
        product_id=product.id,
        image_url=img_in.image_url,
        sort_order=img_in.sort_order,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_image(
    product_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Removes a photo from a product."""
    image = db.query(models.ProductImage).filter(
        models.ProductImage.id == image_id,
        models.ProductImage.product_id == product_id
    ).first()
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product.vendor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this product")

    db.delete(image)
    db.commit()
    return None
