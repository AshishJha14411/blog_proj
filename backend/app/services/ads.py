from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional, Tuple
import uuid
from datetime import datetime

from app.models.ads import Ads
from app.schemas.ads import AdCreate, AdUpdate

# --- Admin CRUD Functions ---

def create_ad(db: Session, data: AdCreate) -> Ads:
    """Creates a new ad in the database."""
    # Use model_dump() for Pydantic v2
    ad_data = data.model_dump(mode="json")
    # The schema now uses tag_names, but the model doesn't have this field yet.
    # We'll ignore it for now and can add tag relationships later.
    ad_data.pop('tag_names', None)

    ad = Ads(**ad_data)
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad

def update_ad(db: Session, ad_id: uuid.UUID, data: AdUpdate) -> Optional[Ads]:
    ad = db.get(Ads, ad_id)
    if not ad:
        return None

    update_data = data.model_dump(mode="json", exclude_unset=True)  # <- key change
    update_data.pop('tag_names', None)

    for k, v in update_data.items():
        setattr(ad, k, v)
    ad.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ad)
    return ad

def delete_ad(db: Session, ad_id: uuid.UUID) -> bool:
    """Deletes an ad from the database."""
    ad = db.get(Ads, ad_id)
    if not ad:
        return False
    db.delete(ad)
    db.commit()
    return True

def list_ads(db: Session, limit: int, offset: int) -> Tuple[int, List[Ads]]:
    """Lists all ads for the admin panel."""
    query = db.query(Ads)
    total = query.count()
    items = query.order_by(Ads.created_at.desc()).offset(offset).limit(limit).all()
    return total, items

def get_ad(db: Session, ad_id: uuid.UUID) -> Optional[Ads]:
    """Gets a single ad by its ID."""
    return db.get(Ads, ad_id)
