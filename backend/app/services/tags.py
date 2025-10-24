from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.tags import Tag

def list_tags(db: Session):
    return db.query(Tag).order_by(Tag.name).all()

def create_tag(db: Session, name: str, description: str | None) -> Tag:
    existing = db.query(Tag).filter(Tag.name== name).first()
    if existing:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail = "Tag with this name already exists")
    tag = Tag(name=name, description=description)
    db.add(tag)
    db.commit()
    
def update_tag(db:Session, tag_id:int, name:str|None, description:str|None) -> Tag:
    tag= db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    
    if name and name != tag.name:
        conflict = db.get(Tag).filter(Tag.name == name).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail = "Another tag with this name already exists")
        tag.anme = name
    if description is not None:
        tag.description = description
    db.commit()
    db.refresh(tag)
    return tag

def delete_tag(db:Session, tag_id: int) -> None:
    tag = db.get(Tag,tag_id)
    if not tag: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    db.delete(tag)
    db.commit()
    