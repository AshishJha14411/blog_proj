from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid # <-- Import uuid for type hinting
from typing import List

from app.schemas.tags import TagCreate, TagUpdate, TagOut, TagList
from app.services.tags import list_tags, create_tag, update_tag, delete_tag
from app.dependencies import get_db, require_roles

router = APIRouter(prefix="/tags", tags=["Tags"])

@router.get("/", response_model=TagList, status_code=status.HTTP_200_OK)
def read_tags(db: Session = Depends(get_db)):
    tags_from_db = list_tags(db)
    
    # --- FIX: Manually build the response to handle UUID -> str conversion ---
    validated_tags = [
        TagOut(id=str(tag.id), name=tag.name, description=tag.description) for tag in tags_from_db
    ]
    return TagList(tags=validated_tags)


@router.post("/", response_model=TagOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("creator", "superadmin"))])
def add_tag(data: TagCreate, db: Session = Depends(get_db)):
    new_tag = create_tag(db, name=data.name, description=data.description)
    return new_tag # Pydantic will auto-convert here, but manual is safer

@router.patch("/{tag_id}", response_model=TagOut, status_code=status.HTTP_200_OK, dependencies=[Depends(require_roles("superadmin"))])
def change_tag(
    tag_id: uuid.UUID, # <-- FIX: Changed from int to uuid.UUID
    data: TagUpdate,
    db: Session = Depends(get_db)
):
    updated_tag = update_tag(db, tag_id, name=data.name, description=data.description)
    return updated_tag

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("superadmin"))])
def remove_tag(
    tag_id: uuid.UUID, # <-- FIX: Changed from int to uuid.UUID
    db: Session = Depends(get_db)
):
    delete_tag(db, tag_id)
