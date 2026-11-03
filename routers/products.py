from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    condition: Optional[models.ProductCondition] = Query(None, description="Filter by condition"),
    min_price_kobo: Optional[int] = Query(None, ge=0, description="Minimum price in kobo"),
    max_price_kobo: Optional[int] = Query(None, ge=0, description="Maximum price in kobo"),
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor"),
    university: Optional[str] = Query(None, description="University filter"),
    scope: Optional[str] = Query(None, description="Scope (e.g. campus, trending)"),
    is_rental: Optional[int] = Query(None, description="Rental filter"),
    sort: Optional[str] = Query(None, description="Sort order (newest, price_asc, price_desc)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Search and browse marketplace products at FUT Minna.
    """
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
        query = query.filter(models.Product.condition == condition)

    if min_price_kobo is not None:
        query = query.filter(models.Product.price_kobo >= min_price_kobo)

    if max_price_kobo is not None:
        query = query.filter(models.Product.price_kobo <= max_price_kobo)

    if vendor_id:
        query = query.filter(models.Product.vendor_id == vendor_id)

    if sort == "price_asc":
        query = query.order_by(models.Product.price_kobo.asc())
    elif sort == "price_desc":
        query = query.order_by(models.Product.price_kobo.desc())
    else:
        query = query.order_by(models.Product.created_at.desc())

    return query.offset(offset).limit(limit).all()

@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """Retrieves single product details."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product

@router.post("", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    prod_in: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Creates a new product listing (Any authenticated student can list items).
    """
    # Verify category exists (with resilient UUID and fallback handling)
    category = None
    try:
        cat_uuid = UUID(str(prod_in.category_id))
        category = db.query(models.Category).filter(models.Category.id == cat_uuid).first()
    except (ValueError, TypeError, AttributeError):
        pass

    if not category:
        category = db.query(models.Category).first()
        if not category:
            category = models.Category(name="General Campus Marketplace")
            db.add(category)
            db.commit()
            db.refresh(category)

    # Auto-provision vendor profile if not already present
    if not current_user.vendor_profile:
        store_name = f"{current_user.full_name}'s Campus Store"
        # Check unique store name
        existing_store = db.query(models.VendorProfile).filter(models.VendorProfile.store_name == store_name).first()
        if existing_store:
            store_name = f"{current_user.full_name} ({str(current_user.id)[:4]})"
        vendor_prof = models.VendorProfile(
            user_id=current_user.id,
            store_name=store_name,
            store_description="Student seller at FUT Minna",
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
        location=prod_in.location or current_user.location or "FUT Minna Bosso/Gidan Kwano",
        prep_time_minutes=prod_in.prep_time_minutes,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # Attach images if provided
    if prod_in.images:
        for idx, img in enumerate(prod_in.images):
            image_record = models.ProductImage(
                product_id=product.id,
                image_url=img.image_url,
                sort_order=img.sort_order if img.sort_order else idx,
            )
            db.add(image_record)
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
    """Updates product attributes (Owner vendor or Admin)."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.vendor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this product")

    if prod_in.category_id is not None:
        cat = db.query(models.Category).filter(models.Category.id == prod_in.category_id).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        product.category_id = prod_in.category_id

    if prod_in.title is not None:
        product.title = prod_in.title
    if prod_in.description is not None:
        product.description = prod_in.description
    if prod_in.condition is not None:
        product.condition = prod_in.condition
    if prod_in.price_kobo is not None:
        product.price_kobo = prod_in.price_kobo
    if prod_in.stock is not None:
        product.stock = prod_in.stock
    if prod_in.status is not None:
        product.status = prod_in.status
    if prod_in.location is not None:
        product.location = prod_in.location
    if prod_in.prep_time_minutes is not None:
        product.prep_time_minutes = prod_in.prep_time_minutes

    db.commit()
    db.refresh(product)
    return product

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
    current_user: models.User = Depends(auth.require_vendor)
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
    current_user: models.User = Depends(auth.require_vendor)
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
