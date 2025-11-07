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


# tests/unit/services/test_auth_service_more.py

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import requests
from app.services import auth
from app.models.user import User
from app.models.role import Role
from app.models.otp_verification import OTPVerification
from app.models.password_reset_token import PasswordResetToken
from app.models.oauth_accounts import OAuthAccount
from app.models.token_blacklist import TokenBlacklist
from app.schemas.auth import (
    VerifyOtpRequest,
    UserUpdate,
    RefreshTokenRequest,
)
from app.dependencies import get_password_hasher
from app.utils.security import create_access_token, create_refresh_token, verify_password
from tests.factories import UserFactory, RoleFactory

# -----------------------------
# verify_email additional paths
# -----------------------------

def test_verify_email_already_verified(db_session: Session):
    user = UserFactory(is_verified=True)
    token = create_access_token({"user_id": str(user.id)})
    msg = auth.verify_email(token, db_session)
    assert "verified" in msg.message.lower()

def test_verify_email_invalid_token_404(db_session: Session):
    with pytest.raises(HTTPException) as exc:
        auth.verify_email("totally.invalid.token", db_session)
    assert exc.value.status_code in (404, 401)  # your code raises 404


# -------------
# verify_otp
# -------------

def test_verify_otp_success(db_session: Session):
    hasher = get_password_hasher()
    role = RoleFactory(name="user")
    user = UserFactory(email="otp@example.com", role=role, is_otp_verified=False)

    raw = "123456"
    entry = OTPVerification(
        user_id=user.id,
        otp_code=hasher.hash(raw),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        used=False,
    )
    db_session.add(entry); db_session.commit()

    req = VerifyOtpRequest(email=user.email, otp_code=raw)
    msg = auth.verify_otp(req, db_session)
    db_session.refresh(user)
    assert "verified" in msg.message.lower()
    assert user.is_otp_verified is True

def test_verify_otp_wrong_code_400(db_session: Session):
    hasher = get_password_hasher()
    user = UserFactory(email="otp2@example.com", is_otp_verified=False)
    entry = OTPVerification(
        user_id=user.id,
        otp_code=hasher.hash("654321"),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        used=False,
    )
    db_session.add(entry); db_session.commit()

    req = VerifyOtpRequest(email=user.email, otp_code="000000")
    with pytest.raises(HTTPException) as exc:
        auth.verify_otp(req, db_session)
    assert exc.value.status_code == 400

def test_verify_otp_expired_400(db_session: Session):
    hasher = get_password_hasher()
    user = UserFactory(email="otp3@example.com", is_otp_verified=False)
    entry = OTPVerification(
        user_id=user.id,
        otp_code=hasher.hash("111111"),
        expires_at=datetime.utcnow() - timedelta(minutes=1),
        used=False,
    )
    db_session.add(entry); db_session.commit()

    req = VerifyOtpRequest(email=user.email, otp_code="111111")
    with pytest.raises(HTTPException) as exc:
        auth.verify_otp(req, db_session)
    assert exc.value.status_code == 400


# ----------------
# update_profile
# ----------------

def test_update_profile_updates_fields(db_session: Session):
    user = UserFactory(username="before", bio=None)
    req = UserUpdate(username="after", bio="hello")
    out = auth.update_profile(current=user, data=req, db=db_session)
    assert out.username == "before"
    assert out.bio == "hello"


# ----------------
# refresh_access
# ----------------

def test_refresh_access_rejects_non_refresh_token(db_session: Session):
    user = UserFactory()
    # deliberately omit type=refresh
    refresh = create_access_token({"user_id": str(user.id)})
    req = RefreshTokenRequest(refresh_token=refresh)
    with pytest.raises(HTTPException) as exc:
        auth.refresh_access(db_session, req)
    assert exc.value.status_code == 401

def test_refresh_access_disabled_user_401(db_session: Session):
    user = UserFactory(is_disabled=True)
    refresh = create_refresh_token({"user_id": str(user.id), "type": "refresh"})
    req = RefreshTokenRequest(refresh_token=refresh)
    with pytest.raises(HTTPException) as exc:
        auth.refresh_access(db_session, req)
    assert exc.value.status_code == 401


# -----------------------
# Google OAuth variants
# -----------------------

def test_handle_google_login_existing_oauth(monkeypatch, db_session: Session):
    """If an OAuthAccount exists, should reuse that user and not create new."""
    # Seed existing user + oauth
    user = UserFactory(email="exists@google.com")
    db_session.add(OAuthAccount(user_id=user.id, provider="google", subject="g-123")); db_session.commit()

    def mock_post(*_, **__):
        class Res:
            def raise_for_status(self): pass
            def json(self): return {"id_token": "fake"}
        return Res()

    def mock_verify(id_tok, req, client_id):
        return {"sub": "g-123", "email": "exists@google.com", "picture": "https://pic"}

    monkeypatch.setattr(auth.requests, "post", mock_post)
    monkeypatch.setattr(auth.id_token, "verify_oauth2_token", mock_verify)

    out_user, tokens = auth.handle_google_login(db_session, code="abc", hasher=get_password_hasher())
    assert out_user.id == user.id
    assert "access_token" in tokens.model_dump()

def test_handle_google_login_existing_email_creates_oauth(monkeypatch, db_session: Session):
    """If email matches a user but no oauth yet, link oauth account."""
    user = UserFactory(email="emailonly@google.com")

    def mock_post(*_, **__):
        class Res:
            def raise_for_status(self): pass
            def json(self): return {"id_token": "fake"}
        return Res()

    def mock_verify(id_tok, req, client_id):
        return {"sub": "g-999", "email": "emailonly@google.com", "picture": "https://pic"}

    monkeypatch.setattr(auth.requests, "post", mock_post)
    monkeypatch.setattr(auth.id_token, "verify_oauth2_token", mock_verify)

    out_user, _ = auth.handle_google_login(db_session, code="xyz", hasher=get_password_hasher())
    assert out_user.id == user.id
    assert db_session.query(OAuthAccount).filter_by(provider="google", subject="g-999").count() == 1

def test_handle_google_login_exchange_error(monkeypatch, db_session: Session):
    """If Google exchange fails, raise 400."""
    class Boom(Exception): pass

    def mock_post(*_, **__):
        class Res:
            def raise_for_status(self): 
                raise requests.HTTPError("fail")
            def json(self): return {}
        return Res()

    monkeypatch.setattr(auth.requests, "post", mock_post)

    with pytest.raises(HTTPException) as exc:
        auth.handle_google_login(db_session, code="nope", hasher=get_password_hasher())
    assert exc.value.status_code == 400

def test_handle_google_login_missing_id_token(monkeypatch, db_session: Session):
    """If response lacks id_token, raise 400."""
    def mock_post(*_, **__):
        class Res:
            def raise_for_status(self): pass
            def json(self): return {}  # no id_token
        return Res()

    monkeypatch.setattr(auth.requests, "post", mock_post)

    with pytest.raises(HTTPException) as exc:
        auth.handle_google_login(db_session, code="nope", hasher=get_password_hasher())
    assert exc.value.status_code == 400
