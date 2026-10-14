from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import auth

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("", response_model=List[schemas.CategoryOut])
def get_categories(
    parent_only: bool = Query(False, description="Filter for top-level categories only"),
    db: Session = Depends(get_db)
):
    """Lists marketplace categories."""
    query = db.query(models.Category)
    if parent_only:
        query = query.filter(models.Category.parent_id.is_(None))
    return query.order_by(models.Category.name).all()

@router.post("", response_model=schemas.CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """Creates a new category or subcategory (Admin only)."""
    if db.query(models.Category).filter(models.Category.name == category_in.name).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists")

    if category_in.parent_id:
        parent = db.query(models.Category).filter(models.Category.id == category_in.parent_id).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found")

    category = models.Category(
        name=category_in.name,
        description=category_in.description,
        parent_id=category_in.parent_id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@router.patch("/{category_id}", response_model=schemas.CategoryOut)
def update_category(
    category_id: UUID,
    category_in: schemas.CategoryUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """Updates category details (Admin only)."""
    cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if category_in.name is not None:
        cat.name = category_in.name
    if category_in.description is not None:
        cat.description = category_in.description
    if category_in.parent_id is not None:
        cat.parent_id = category_in.parent_id

    db.commit()
    db.refresh(cat)
    return cat

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """Deletes a category (Admin only)."""
    cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    db.delete(cat)
    db.commit()
    return None
