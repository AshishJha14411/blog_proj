# tests/unit/services/test_system_service.py
import uuid
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.services.system import get_automod_user
from app.models.user import User
from app.models.role import Role
from tests.factories import RoleFactory, UserFactory  # RoleFactory has get-or-create behavior

def test_get_automod_user_creates_if_missing(db_session: Session):
    u = get_automod_user(db_session)
    assert u.username == "automod"
    again = get_automod_user(db_session)
    assert again.id == u.id  # idempotent


def test_get_automod_user_returns_existing(db_session: Session):
    # ✅ Reuse existing moderator role (or create if absent) without violating unique constraint
    role = db_session.query(Role).filter_by(name="moderator").first() or RoleFactory(name="moderator")

    u = User(
        email="automod@system.local",
        username="automod",
        password_hash="!",
        is_verified=True,
        role_id=role.id,
    )
    db_session.add(u)
    db_session.commit()

    out = get_automod_user(db_session)
    assert out.id == u.id


from unittest.mock import MagicMock  # Make sure this is imported at the top
from sqlalchemy.exc import IntegrityError # Make sure this is imported
from app.models.user import User # Make sure this is imported
from app.models.role import Role # Make sure this is imported

def test_get_automod_user_race_safe(db_session: Session, monkeypatch):
    """
    Simulate a race condition by mocking DB calls.
    Service should rollback, refetch, and return the row.
    """
    # ARRANGE
    # 1. Create the 'moderator' role and commit it.
    mod_role = RoleFactory(name="moderator")
    db_session.commit() # Commit it so the service can find it

    # 2. This is the 'mock' user that the 'other process' created.
    #    We use .build() so it's just an object, not in the DB.
    mock_automod_user = UserFactory.build(
        username="automod",
        email="automod@system.local",
        role=RoleFactory.build(name="moderator")
    )

    # --- THIS IS THE FIX ---
    
    # 3. Create separate mocks for the User query
    mock_user_query = MagicMock()
    mock_user_filter = MagicMock()
    mock_user_query.filter.return_value = mock_user_filter
    # This side_effect is *only* for the User query
    mock_user_filter.first.side_effect = [None, mock_automod_user]

    # 4. Create separate mocks for the Role query
    mock_role_query = MagicMock()
    mock_role_filter = MagicMock()
    mock_role_query.filter.return_value = mock_role_filter
    # This mock will *always* return the real role
    mock_role_filter.first.return_value = mod_role 

    # 5. Create a "router" for db.query
    #    This is the key to the solution.
    real_query = db_session.query # Save the original
    def query_router(model_class):
        if model_class is User:
            return mock_user_query
        if model_class is Role:
            return mock_role_query
        return real_query(model_class) # Pass through any other queries

    monkeypatch.setattr(db_session, "query", query_router)

    # 6. Mock flush() and rollback()
    class DummyOrig(Exception): pass
    def mock_flush_that_fails(*args, **kwargs):
        # We only need to fail if the automod user is being added
        if any(isinstance(obj, User) and obj.username == "automod" for obj in db_session.new):
            raise IntegrityError("Simulated race condition", params={}, orig=DummyOrig("dup"))
    
    monkeypatch.setattr(db_session, "flush", mock_flush_that_fails)
    monkeypatch.setattr(db_session, "rollback", lambda: None)
    
    # --- END FIX ---

    # ACT
    # The service will now:
    # 1. Call db.query(User) -> hits mock_user_query -> returns None
    # 2. Call db.query(Role) -> hits mock_role_query -> returns mod_role
    # 3. Call db.flush() -> mock_flush_that_fails() raises IntegrityError
    # 4. Call db.rollback() -> does nothing
    # 5. Call db.query(User) -> hits mock_user_query -> returns mock_automod_user
    user = get_automod_user(db_session)

    # ASSERT
    assert user is mock_automod_user
    assert user.username == "automod"
    assert mock_user_filter.first.call_count == 2 # Proves both User queries ran
    assert mock_role_filter.first.call_count == 1 # Proves the Role query ran