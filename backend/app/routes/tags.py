# app/routes/tags.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid
from app.models.user import User
from app.schemas.tags import TagCreate, TagUpdate, TagOut, TagList
from app.services.tags import list_tags, create_tag, update_tag, delete_tag
from app.dependencies import get_db
from app import dependencies as deps  # import the module, not the function

router = APIRouter(prefix="/tags", tags=["Tags"])

# ✅ define these ONCE at module level so tests can import the exact same objects
creator_or_superadmin = deps.require_roles("creator", "superadmin")
superadmin_only = deps.require_roles("superadmin")


@router.get("/", response_model=TagList, status_code=status.HTTP_200_OK)
def read_tags(db: Session = Depends(get_db)):
    tags = list_tags(db)
    return TagList(tags=[TagOut(id=str(t.id), name=t.name, description=t.description) for t in tags])


@router.post("/", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def add_tag(
    data: TagCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(creator_or_superadmin),     # ✅ use the shared callable
):
    tag = create_tag(db, name=data.name, description=data.description)
    return TagOut(id=str(tag.id), name=tag.name, description=tag.description)


@router.patch("/{tag_id}", response_model=TagOut, status_code=status.HTTP_200_OK)
def change_tag(
    tag_id: uuid.UUID,
    data: TagUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(superadmin_only),           # ✅ use the shared callable
):
    tag = update_tag(db, tag_id, name=data.name, description=data.description)
    return TagOut(id=str(tag.id), name=tag.name, description=tag.description)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag(
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(superadmin_only),           # ✅ use the shared callable
):
    delete_tag(db, tag_id)
