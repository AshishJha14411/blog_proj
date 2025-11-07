# app/services/tags.py

from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.tags import Tag

def list_tags(db: Session) -> list[Tag]:
    return db.query(Tag).order_by(Tag.name.asc()).all()

def create_tag(db: Session, name: str, description: str | None) -> Tag:
    existing = db.query(Tag).filter(Tag.name == name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag with this name already exists",
        )
    tag = Tag(name=name, description=description)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

def update_tag(
    db: Session,
    tag_id: UUID,                      # IDs are UUIDs in your models
    name: str | None,
    description: str | None,
) -> Tag:
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tag not found")

    if name and name != tag.name:
        conflict = db.query(Tag).filter(Tag.name == name).first()
        if conflict:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Another tag with this name already exists",
            )
        tag.name = name  # fixed typo

    if description is not None:
        tag.description = description

    db.commit()
    db.refresh(tag)
    return tag

def delete_tag(db: Session, tag_id: UUID) -> None:
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tag not found")
    db.delete(tag)
    db.commit()
