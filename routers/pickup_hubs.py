from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from services import auth

router = APIRouter(prefix="/pickup-hubs", tags=["Pickup Hubs"])

@router.get("", response_model=List[schemas.PickupHubOut])
def list_pickup_hubs(
    campus: str = "FUT Minna",
    db: Session = Depends(get_db)
):
    """Lists official campus pickup hubs."""
    return db.query(models.PickupHub).filter(
        models.PickupHub.campus == campus,
        models.PickupHub.is_active == True
    ).all()

@router.get("/{hub_id}", response_model=schemas.PickupHubOut)
def get_pickup_hub(hub_id: UUID, db: Session = Depends(get_db)):
    """Retrieves details of an individual pickup hub."""
    hub = db.query(models.PickupHub).filter(models.PickupHub.id == hub_id).first()
    if not hub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pickup hub not found")
    return hub

@router.post("", response_model=schemas.PickupHubOut, status_code=status.HTTP_201_CREATED)
def create_pickup_hub(
    hub_in: schemas.PickupHubCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin)
):
    """Creates a new campus pickup hub (Admin only)."""
    hub = models.PickupHub(
        name=hub_in.name,
        campus=hub_in.campus,
        location=hub_in.location,
        coordinates=hub_in.coordinates,
        image_url=hub_in.image_url,
        is_active=True,
    )
    db.add(hub)
    db.commit()
    db.refresh(hub)
    return hub
