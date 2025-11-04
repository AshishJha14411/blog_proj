import pytest
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import secrets
import uuid

from app.services import auth
from app.models.user import User
from app.models.role import Role
from app.models.otp_verification import OTPVerification
from app.models.password_reset_token import PasswordResetToken
from app.models.token_blacklist import TokenBlacklist
from app.models.oauth_accounts import OAuthAccount
from app.schemas.auth import (
    LoginRequest,
    SignUpRequest,
    PasswordChangeRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RefreshTokenRequest,
    VerifyOtpRequest,
)
from app.utils.security import  verify_password, create_access_token, create_refresh_token
from app.dependencies import get_password_hasher
from tests.factories import UserFactory, RoleFactory, PasswordResetTokenFactory


# ----------------------------------------------------------------------
# CREATE USER
# ----------------------------------------------------------------------
def test_create_user_success(db_session: Session, dummy_mailer, run_bg_tasks):
    """A new user should be created and OTP email tasks scheduled."""
    hasher = get_password_hasher()
    bg = BackgroundTasks()
    data = SignUpRequest(email="test@example.com", username="testuser", password="strongpassword")
    user, tokens = auth.create_user(
        db=db_session, data=data, background_tasks=bg,
        hasher=hasher, mailer=dummy_mailer
    )
    run_bg_tasks(bg)
    assert user.email == "test@example.com"
    assert user.role.name == "user"
    assert isinstance(tokens.access_token, str)
    assert len(dummy_mailer.outbox) == 2  # OTP + verification emails


def test_create_user_conflict(db_session: Session, dummy_mailer):
    """Should raise 409 if email or username already exists."""
    existing = UserFactory(email="dupe@example.com", username="dupeuser")
    hasher = get_password_hasher()
    bg = BackgroundTasks()

    data = type("SignUp", (), {
        "email": existing.email,
        "username": existing.username,
        "password": "password123"
    })()

    with pytest.raises(HTTPException) as exc_info:
        auth.create_user(db_session, data, bg, hasher, dummy_mailer)
    assert exc_info.value.status_code == 409


# ----------------------------------------------------------------------
# LOGIN
# ----------------------------------------------------------------------
def test_login_user_success(db_session: Session):
    """Login succeeds with valid credentials."""
    hasher = get_password_hasher()
    pw = "password123"
    user = UserFactory(password_hash=hasher.hash(pw), username="demo")

    login = LoginRequest(username="demo", password=pw)
    u, tokens = auth.login_user(db=db_session, data=login, hasher=hasher)

    assert u.id == user.id
    assert "access_token" in tokens.model_dump()
    assert "refresh_token" in tokens.model_dump()


def test_login_user_invalid_password(db_session: Session):
    """Should raise 401 for wrong password."""
    user = UserFactory(username="demo2", password_hash=get_password_hasher().hash("right"))
    bad_login = LoginRequest(username="demo2", password="wrongpassword")

    with pytest.raises(HTTPException) as exc_info:
        auth.login_user(db=db_session, data=bad_login, hasher=get_password_hasher())
    assert exc_info.value.status_code == 401


def test_login_user_not_found(db_session: Session):
    """Should raise 401 for nonexistent user."""
    data = LoginRequest(username="ghost", password="password123")
    with pytest.raises(HTTPException):
        auth.login_user(db_session, data, get_password_hasher())


# ----------------------------------------------------------------------
# LOGOUT
# ----------------------------------------------------------------------
def test_logout_user_success(db_session: Session):
    """Blacklists a valid refresh token."""
    user = UserFactory()
    refresh = create_refresh_token({"user_id": str(user.id)})

    res = auth.logout_user(db_session, refresh)
    assert res["message"] == "You have been successfully logged out"
    assert db_session.query(TokenBlacklist).count() == 1


def test_logout_user_invalid_token_does_not_fail(db_session: Session):
    """Invalid token should silently succeed."""
    res = auth.logout_user(db_session, "malformed_token")
    assert res["message"] == "You have been successfully logged out"


# ----------------------------------------------------------------------
# VERIFY EMAIL
# ----------------------------------------------------------------------
def test_verify_email_sets_flag(db_session: Session):
    """Decodes token and verifies the user."""
    user = UserFactory(is_verified=False)
    token = create_access_token({"user_id": str(user.id)})

    msg = auth.verify_email(token, db_session)
    db_session.refresh(user)
    assert msg.message.lower().startswith("email is verified")
    assert user.is_verified is True


# ----------------------------------------------------------------------
# CHANGE PASSWORD
# ----------------------------------------------------------------------
def test_change_password_success(db_session: Session):
    """Should update password when old password matches."""
    hasher = get_password_hasher()
    user = UserFactory(password_hash=hasher.hash("oldpass"))
    req = PasswordChangeRequest(old_password="oldpass", new_password="newpassword")

    res = auth.change_password(user, req, hasher, db_session)
    assert res["message"].startswith("Password changed")
    db_session.refresh(user)
    assert verify_password("newpassword", user.password_hash)


def test_change_password_wrong_old(db_session: Session):
    """Should raise 400 for invalid old password."""
    user = UserFactory(password_hash=get_password_hasher().hash("old"))
    req = PasswordChangeRequest(old_password="wrong", new_password="newpassword")

    with pytest.raises(HTTPException) as exc_info:
        auth.change_password(user, req, get_password_hasher(), db_session)
    assert exc_info.value.status_code == 400


# ----------------------------------------------------------------------
# FORGOT / RESET PASSWORD
# ----------------------------------------------------------------------
import inspect
import asyncio

def _drain_background_tasks(bg: BackgroundTasks):
    for task in bg.tasks:
        res = task.func(*task.args, **task.kwargs)
        if inspect.iscoroutine(res):
            asyncio.get_event_loop().run_until_complete(res)
            
def test_forgot_password_generates_token(db_session: Session, dummy_mailer,run_bg_tasks):
    user = UserFactory(email="reset@example.com")
    data = ForgotPasswordRequest(email=user.email)
    bg = BackgroundTasks()

    res = auth.forgot_password(db_session, data, bg, dummy_mailer)
    run_bg_tasks(bg)

    assert res["message"].startswith("If an account")
    assert db_session.query(PasswordResetToken).filter_by(user_id=user.id).count() == 1
    assert len(dummy_mailer.outbox) == 1

def test_reset_password_success(db_session: Session):
    """Resets password with valid token."""
    hasher = get_password_hasher()
    user = UserFactory(password_hash=hasher.hash("oldpw"))
    token = PasswordResetToken(
        user_id=user.id,
        token="token123",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        used=False
    )
    db_session.add(token)
    db_session.commit()

    req = ResetPasswordRequest(token="token123", new_password="newpassword")
    res = auth.reset_password(db_session, req, hasher)
    db_session.refresh(user)

    assert res["message"].startswith("Your password has been reset")
    assert verify_password("newpassword", user.password_hash)
    assert token.used is True


def test_reset_password_invalid_or_expired(db_session: Session):
    user = UserFactory()
    expired = PasswordResetTokenFactory(
        user_id=user.id,
        token="expired",
        expires_at=datetime.utcnow() - timedelta(hours=1),
        used=False,
    )
    db_session.add(expired)
    db_session.commit()

    req = ResetPasswordRequest(token="expired", new_password="newpassword")
    with pytest.raises(HTTPException) as exc:
        auth.reset_password(db_session, req, get_password_hasher())
    assert exc.value.status_code == 400


# ----------------------------------------------------------------------
# REFRESH TOKEN
# ----------------------------------------------------------------------
def test_refresh_access_success(db_session: Session):
    """Valid refresh token should issue new access token."""
    user = UserFactory()
    refresh = create_refresh_token({"user_id": str(user.id), "type": "refresh"})
    req = RefreshTokenRequest(refresh_token=refresh)

    user_out, tokens = auth.refresh_access(db_session, req)
    assert user_out.id == user.id
    assert "access_token" in tokens.model_dump()


def test_refresh_access_blacklisted(db_session: Session):
    """Blacklisted refresh token should fail."""
    user = UserFactory()
    refresh = create_refresh_token({"user_id": str(user.id), "type": "refresh"})
    payload = auth.decode_access_token(refresh)
    db_session.add(TokenBlacklist(jti=payload["jti"], expires_at=datetime.now(timezone.utc)))
    db_session.commit()

    req = RefreshTokenRequest(refresh_token=refresh)
    with pytest.raises(HTTPException) as exc_info:
        auth.refresh_access(db_session, req)
    assert "Invalid or expired refresh token" in str(exc_info.value.detail)


# ----------------------------------------------------------------------
# GOOGLE OAUTH (mocked)
# ----------------------------------------------------------------------
def test_handle_google_login_new_user(monkeypatch, db_session: Session):
    """Should create new user + oauth record when first-time Google login."""
    mock_resp = {
        "id_token": "fake_id_token"
    }

    def mock_post(*_, **__):
        class Res:
            def raise_for_status(self): pass
            def json(self): return mock_resp
        return Res()

    def mock_verify(id_tok, req, client_id):
        return {"sub": "google123", "email": "test@google.com", "picture": "https://pic"}
    
    monkeypatch.setattr(auth.requests, "post", mock_post)
    monkeypatch.setattr(auth.id_token, "verify_oauth2_token", mock_verify)

    user, tokens = auth.handle_google_login(db_session, code="123", hasher=get_password_hasher())
    assert user.email == "test@google.com"
    assert db_session.query(OAuthAccount).filter_by(provider="google").count() == 1
    assert "access_token" in tokens.model_dump()
