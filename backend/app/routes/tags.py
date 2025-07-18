from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas.tags import TagCreate, TagUpdate, TagOut, TagList
from app.services.tags import list_tags, create_tag, update_tag, delete_tag
from app.dependencies import get_db, require_roles

router = APIRouter(prefix="/tags", tags=["Tags"])

@router.get("/",response_model = TagList, status_code=status.HTTP_200_OK)
def read_tags(db:Session = Depends(get_db)):
    tags = list_tags(db)
    return TagList(tags = tags)

@router.post("/",response_model=TagOut, status_code = status.HTTP_201_CREATED, dependencies = [Depends(require_roles("creator","superadmin"))])
def add_tag(data:TagCreate, db:Session = Depends(get_db)):
    return create_tag(db,name=data.name, description=data.description)

@router.patch("/{tag_id}", response_model = TagOut, status_code = status.HTTP_200_OK, dependencies=[Depends(require_roles("superadmin"))])

def change_tag(
    tag_id: int,
    data: TagUpdate,
    db: Session = Depends(get_db)
):
    return update_tag(db,tag_id, name=data.name, description = data.description)

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies = [Depends(require_roles("superadmin"))])
def remove_tag(tag_id: int, db: Session = Depends(get_db)):
    delete_tag(db, tag_id)