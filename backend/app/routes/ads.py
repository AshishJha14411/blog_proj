from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies import get_db, require_roles, get_current_user_optional
from app.schemas.ads import AdCreate, AdUpdate, AdOut, ServeAdOut, AdList
from app.services.ads import (
    serve_ad, log_impression, log_click,
    create_ad, update_ad, delete_ad, list_ads, get_ad
)
from app.services.audit import audit

router = APIRouter(prefix="/ads", tags=["Ads"])

@router.get("/serve", response_model=Optional[ServeAdOut])
def serve(
    slot: str = Query(...),
    post_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    ad = serve_ad(db, slot)
    if not ad: return None
    return ServeAdOut(
        id=ad.id,
        advertiser_name=ad.advertiser_name,
        ad_content=ad.ad_content,
        image_url=ad.image_url,
        destination_url=ad.destination_url,
        slot=ad.slot
    )

@router.post("/impression", status_code=status.HTTP_204_NO_CONTENT)
def impression(
    ad_id: int = Query(...),
    slot: str = Query(...),
    post_id: Optional[int] = Query(None),
    request: Request = None,
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request else None
    ua = request.headers.get("user-agent") if request else None
    log_impression(
        db,
        ad_id=ad_id,
        slot=slot,
        post_id=post_id,
        user_id=(current_user.id if current_user else None),
        ip=ip,
        user_agent=ua,
    )
    return

@router.get("/click")
def click(
    ad_id: int = Query(...),
    post_id: Optional[int] = Query(None),
    request: Request = None,
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    ad = get_ad(db, ad_id)
    if not ad or not ad.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ad not found")

    ip = request.client.host if request else None
    ua = request.headers.get("user-agent") if request else None

    # store click using your Click model
    log_click(
        db,
        ad_id=ad_id,
        post_id=post_id,
        user_id=(current_user.id if current_user else None),
        ip=ip,
        user_agent=ua,
    )

    # 302 to destination
    return RedirectResponse(url=ad.destination_url, status_code=status.HTTP_302_FOUND)

# --- Admin CRUD ---

@router.post("/", response_model=AdOut)
def create_ad_route(
    body: AdCreate,
    db: Session = Depends(get_db),
    request: Request = None,
    admin = Depends(require_roles("moderator", "superadmin")),
):
    ad = create_ad(db, body)
    audit(
        db,
        actor_user_id=admin.id,
        action="ad_create",
        target_type="ad",
        target_id=ad.id,
        details=f"Created ad in slot {ad.slot}",
        ip=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    return ad

@router.get("/", response_model=AdList)
def list_ads_route(
    slot: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin = Depends(require_roles("moderator", "superadmin")),
):
    total, items = list_ads(db, slot, active, limit, offset)
    return AdList(total=total, limit=limit, offset=offset, items=items)

@router.get("/{ad_id}", response_model=AdOut)
def get_ad_route(
    ad_id: int,
    db: Session = Depends(get_db),
    admin = Depends(require_roles("moderator", "superadmin")),
):
    ad = get_ad(db, ad_id)
    if not ad:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ad not found")
    return ad

@router.patch("/{ad_id}", response_model=AdOut)
def update_ad_route(
    ad_id: int,
    body: AdUpdate,
    db: Session = Depends(get_db),
    request: Request = None,
    admin = Depends(require_roles("moderator", "superadmin")),
):
    ad = update_ad(db, ad_id, body)
    if not ad:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ad not found")
    audit(
        db,
        actor_user_id=admin.id,
        action="ad_update",
        target_type="ad",
        target_id=ad.id,
        details="Updated ad",
        ip=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    return ad

@router.delete("/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ad_route(
    ad_id: int,
    db: Session = Depends(get_db),
    request: Request = None,
    admin = Depends(require_roles("moderator", "superadmin")),
):
    from app.services.ads import delete_ad
    ok = delete_ad(db, ad_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ad not found")
    audit(
        db,
        actor_user_id=admin.id,
        action="ad_delete",
        target_type="ad",
        target_id=ad_id,
        details="Deleted ad",
        ip=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    return
