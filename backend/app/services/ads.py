import random
from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.ads import Ad
from app.models.impression import Impression
from app.models.click import Click

def _eligible_ads_query(db: Session, slot: str):
    now = datetime.utcnow()
    return (
        db.query(Ad)
        .filter(
            Ad.active == True,
            Ad.slot == slot,
            or_(Ad.start_at == None, Ad.start_at <= now),
            or_(Ad.end_at == None, Ad.end_at >= now),
        )
    )

def choose_weighted_ad(ads: List[Ad]) -> Optional[Ad]:
    if not ads:
        return None
    weights = [max(1, a.weight or 1) for a in ads]
    return random.choices(ads, weights=weights, k=1)[0]

def serve_ad(db: Session, slot: str) -> Optional[Ad]:
    ads = _eligible_ads_query(db, slot).all()
    return choose_weighted_ad(ads)

def log_impression(
    db: Session,
    *,
    ad_id: int,
    slot: str,
    post_id: Optional[int],
    user_id: Optional[int],
    ip: Optional[str],
    user_agent: Optional[str],
) -> Impression:
    imp = Impression(
        ad_id=ad_id,
        slot=slot,
        post_id=post_id,
        user_id=user_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    db.add(imp)
    db.commit()
    db.refresh(imp)
    return imp

def log_click(
    db: Session,
    *,
    ad_id: int,
    post_id: Optional[int],
    user_id: Optional[int],
    ip: Optional[str],
    user_agent: Optional[str],
) -> Click:
    clk = Click(
        ad_id=ad_id,
        post_id=post_id or 0,  # your model requires not null; pass 0 if truly unknown
        user_id=user_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    db.add(clk)
    db.commit()
    db.refresh(clk)
    return clk

# --- Admin CRUD (unchanged) ---
def create_ad(db: Session, data) -> Ad:
    ad = Ad(**data.dict())
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad

def update_ad(db: Session, ad_id: int, data) -> Optional[Ad]:
    ad = db.query(Ad).get(ad_id)
    if not ad: return None
    for k, v in data.dict(exclude_unset=True).items():
        setattr(ad, k, v)
    ad.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ad)
    return ad

def delete_ad(db: Session, ad_id: int) -> bool:
    ad = db.query(Ad).get(ad_id)
    if not ad: return False
    db.delete(ad)
    db.commit()
    return True

def list_ads(db: Session, slot: Optional[str], active: Optional[bool], limit: int, offset: int) -> Tuple[int, List[Ad]]:
    q = db.query(Ad)
    if slot: q = q.filter(Ad.slot == slot)
    if active is not None: q = q.filter(Ad.active == active)
    total = q.count()
    items = q.order_by(Ad.created_at.desc()).offset(offset).limit(limit).all()
    return total, items

def get_ad(db: Session, ad_id: int) -> Optional[Ad]:
    return db.query(Ad).get(ad_id)
