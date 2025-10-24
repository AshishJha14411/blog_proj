from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.dependencies import get_db, require_roles
from app.schemas.ads import AdCreate, AdUpdate, AdOut, AdList
from app.services import ads

# --- 1. Router for ADMIN-ONLY actions ---
# This router is protected and handles creating, updating, and deleting ads.
router = APIRouter(
    prefix="/admin/ads",
    tags=["Admin - Ads"],
    dependencies=[Depends(require_roles("superadmin"))]
)

# --- 2. Router for PUBLIC-FACING actions ---
# This router is open to everyone for viewing ads.
public_router = APIRouter(
    prefix="/ads",
    tags=["Ads"]
)


# --- Public Routes ---

@public_router.get("/", response_model=AdList)
def list_ads(
    db: Session = Depends(get_db),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0)
):
    """Lists all active ads with pagination."""
    total, items = ads.list_ads(db, limit, offset)
    return AdList(total=total, limit=limit, offset=offset, items=items)

@public_router.get("/{ad_id}", response_model=AdOut)
def get_ad(ad_id: uuid.UUID, db: Session = Depends(get_db)):
    """Gets a single ad by its ID."""
    ad = ads.get_ad(db, ad_id)
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
    return AdOut.from_orm(ad)


# --- Admin-Only Routes ---

@router.post("/", response_model=AdOut, status_code=status.HTTP_201_CREATED)
def admin_create_ad(data: AdCreate, db: Session = Depends(get_db)):
    """Admin endpoint to create a new ad."""
    new_ad = ads.create_ad(db, data)
    return AdOut.from_orm(new_ad)

@router.patch("/{ad_id}", response_model=AdOut)
def admin_update_ad(ad_id: uuid.UUID, data: AdUpdate, db: Session = Depends(get_db)):
    """Admin endpoint to update an existing ad."""
    updated_ad = ads.update_ad(db, ad_id, data)
    if not updated_ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
    return AdOut.from_orm(updated_ad)

@router.delete("/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_ad(ad_id: uuid.UUID, db: Session = Depends(get_db)):
    """Admin endpoint to delete an ad."""
    if not ads.delete_ad(db, ad_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
    return None

