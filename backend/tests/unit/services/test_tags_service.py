# tests/unit/services/test_tags_service.py

import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

import app.services.tags as tags_service
from app.models.tags import Tag

def test_list_tags_orders_by_name(db_session: Session):
    db_session.add_all([
        Tag(name="beta", description=None),
        Tag(name="alpha", description=None),
        Tag(name="gamma", description=None),
    ])
    db_session.commit()

    out = tags_service.list_tags(db_session)
    assert [t.name for t in out] == ["alpha", "beta", "gamma"]

def test_create_tag_happy_path(db_session: Session):
    tag = tags_service.create_tag(db_session, "scifi", "Science fiction")
    assert tag.name == "scifi"
    assert tag.description == "Science fiction"
    assert db_session.query(Tag).filter_by(name="scifi").count() == 1

def test_create_tag_conflict_409(db_session: Session):
    db_session.add(Tag(name="dupe")); db_session.commit()
    with pytest.raises(HTTPException) as exc:
        tags_service.create_tag(db_session, "dupe", None)
    assert exc.value.status_code == 409

def test_update_tag_404_when_missing(db_session: Session):
    missing = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        tags_service.update_tag(db_session, missing, name="new", description=None)
    assert exc.value.status_code == 404

def test_update_tag_name_and_description(db_session: Session):
    t = Tag(name="old", description=None); db_session.add(t); db_session.commit()
    out = tags_service.update_tag(db_session, t.id, name="new", description="desc")
    assert out.name == "new"
    assert out.description == "desc"

def test_update_tag_conflict_on_name(db_session: Session):
    a = Tag(name="a"); b = Tag(name="b")
    db_session.add_all([a, b]); db_session.commit()
    with pytest.raises(HTTPException) as exc:
        tags_service.update_tag(db_session, b.id, name="a", description=None)
    assert exc.value.status_code == 409

def test_delete_tag_404_when_missing(db_session: Session):
    with pytest.raises(HTTPException) as exc:
        tags_service.delete_tag(db_session, uuid.uuid4())
    assert exc.value.status_code == 404

def test_delete_tag_happy_path(db_session: Session):
    t = Tag(name="todelete"); db_session.add(t); db_session.commit()
    tags_service.delete_tag(db_session, t.id)
    assert db_session.query(Tag).filter_by(id=t.id).count() == 0
