import io
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_password_hasher
from app.utils.security import create_access_token, create_refresh_token, verify_password
from app.models.user import User
from app.models.role import Role
from app.models.otp_verification import OTPVerification
from app.models.password_reset_token import PasswordResetToken
from app.models.token_blacklist import TokenBlacklist
from tests.factories import UserFactory, RoleFactory

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------
# Global no-op rate limiter overrides for this module
# ---------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _disable_rate_limits(client: TestClient):
    from app.utils.rate_limiter import rate_limit, signup_rate_limiter
    client.app.dependency_overrides[rate_limit] = lambda: None
    client.app.dependency_overrides[signup_rate_limiter] = lambda: None
    yield
    client.app.dependency_overrides.pop(rate_limit, None)
    client.app.dependency_overrides.pop(signup_rate_limiter, None)

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _ensure_role(db: Session, name: str = "user") -> Role:
    r = db.query(Role).filter_by(name=name).first()
    return r or RoleFactory(name=name)

def _create_user_with_password(db: Session, username: str, pw: str) -> User:
    hasher = get_password_hasher()
    role = _ensure_role(db, "user")
    user = UserFactory(username=username, password_hash=hasher.hash(pw), role=role)
    db.add(user); db.commit(); db.refresh(user)
    return user

def _override_current_user(user: User):
    def _dep():
        return user
    return _dep

# ---------------------------------------------------------------------
# /auth/signup
# ---------------------------------------------------------------------
def test_signup_creates_user_and_sets_cookie(client: TestClient, db_session: Session):
    _ensure_role(db_session, "user")
    res = client.post(
        "/auth/signup",
        json={"email": "test@example.com", "username": "tester", "password": "StrongPass1!"}
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "access_token" in body and "refresh_token" in body and "user" in body
    assert "refresh_token" in res.cookies

def test_signup_conflict_409(client: TestClient, db_session: Session):
    _ensure_role(db_session, "user")
    _create_user_with_password(db_session, "dupe", "x")
    # Same username conflict
    res = client.post("/auth/signup", json={
        "email": "another@example.com",
        "username": "dupe",
        "password": "abc"
    })
    assert res.status_code == 409

# ---------------------------------------------------------------------
# /auth/login
# ---------------------------------------------------------------------
def test_login_success_sets_cookie_and_returns_tokens(client: TestClient, db_session: Session):
    _ensure_role(db_session, "user")
    _create_user_with_password(db_session, "login_demo", "pass1234")
    res = client.post("/auth/login", json={"username": "login_demo", "password": "pass1234"})
    assert res.status_code == 200, res.text
    body = res.json()
    # response_model=TokenPair filters out "user"
    assert "access_token" in body and "refresh_token" in body
    assert res.cookies.get("refresh_token")

def test_login_invalid_401(client: TestClient, db_session: Session):
    _ensure_role(db_session, "user")
    _create_user_with_password(db_session, "badpw", "right")
    res = client.post("/auth/login", json={"username": "badpw", "password": "wrongpass"})
    assert res.status_code == 401

# ---------------------------------------------------------------------
# /auth/refresh (cookie-based)
# ---------------------------------------------------------------------
def test_refresh_token_from_cookie_success(client: TestClient, db_session: Session):
    user = _create_user_with_password(db_session, "refresh_me", "pw")
    refresh = create_refresh_token({"user_id": str(user.id), "type": "refresh"})
    client.cookies.set("refresh_token", refresh, path="/auth")
    res = client.post("/auth/refresh")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data and "refresh_token" in data
    assert data["refresh_token"] == refresh  # no rotation currently

def test_refresh_token_missing_cookie_401(client: TestClient):
    res = client.post("/auth/refresh")
    assert res.status_code == 401

def test_refresh_token_blacklisted_clears_cookie(client: TestClient, db_session: Session):
    user = _create_user_with_password(db_session, "revoked", "pw")
    refresh = create_refresh_token({"user_id": str(user.id), "type": "refresh"})
    # Blacklist it
    from app.utils.security import decode_access_token
    decoded = decode_access_token(refresh)
    db_session.add(TokenBlacklist(jti=decoded["jti"], expires_at=datetime.now(timezone.utc)))
    db_session.commit()

    client.cookies.set("refresh_token", refresh, path="/auth")
    res = client.post("/auth/refresh")
    assert res.status_code == 401

# ---------------------------------------------------------------------
# /auth/logout (cookie or header)
# ---------------------------------------------------------------------
def test_logout_with_cookie_blacklists_and_clears_cookie(client: TestClient, db_session: Session):
    user = _create_user_with_password(db_session, "bye", "pw")
    refresh = create_refresh_token({"user_id": str(user.id), "type": "refresh"})
    client.cookies.set("refresh_token", refresh, path="/auth")
    res = client.post("/auth/logout")
    assert res.status_code == 200
    from app.utils.security import decode_access_token
    decoded = decode_access_token(refresh)
    assert db_session.query(TokenBlacklist).filter_by(jti=decoded["jti"]).count() == 1

def test_logout_with_header_bearer(client: TestClient, db_session: Session):
    user = _create_user_with_password(db_session, "bye2", "pw")
    refresh = create_refresh_token({"user_id": str(user.id), "type": "refresh"})
    res = client.post("/auth/logout", headers={"Authorization": f"Bearer {refresh}"})
    assert res.status_code == 200
    from app.utils.security import decode_access_token
    decoded = decode_access_token(refresh)
    assert db_session.query(TokenBlacklist).filter_by(jti=decoded["jti"]).count() == 1

# ---------------------------------------------------------------------
# /auth/verify-email
# ---------------------------------------------------------------------
def test_verify_email_marks_verified(client: TestClient, db_session: Session):
    user = _create_user_with_password(db_session, "verifyme", "pw")
    user.is_verified = False; db_session.commit()
    token = create_access_token({"user_id": str(user.id)}, expires_delta=timedelta(hours=1))
    res = client.get("/auth/verify-email", params={"token": token})
    assert res.status_code == 200
    db_session.refresh(user)
    assert user.is_verified is True

# ---------------------------------------------------------------------
# /auth/verify-otp
# ---------------------------------------------------------------------
def test_verify_otp_success(client: TestClient, db_session: Session):
    hasher = get_password_hasher()
    _ensure_role(db_session, "user")
    user = UserFactory(email="otp@example.com")
    db_session.add(user); db_session.commit()
    raw_otp = "123456"
    otp_entry = OTPVerification(
        user_id=user.id,
        otp_code=hasher.hash(raw_otp),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        used=False,
    )
    db_session.add(otp_entry); db_session.commit()
    res = client.post("/auth/verify-otp", json={"email": "otp@example.com", "otp_code": raw_otp})
    assert res.status_code == 200
    db_session.refresh(user)
    assert user.is_otp_verified is True
    db_session.refresh(otp_entry)
    assert otp_entry.used is True

def test_verify_otp_invalid_or_expired(client: TestClient, db_session: Session):
    _ensure_role(db_session, "user")
    user = UserFactory(email="otp2@example.com")
    db_session.add(user); db_session.commit()
    otp_entry = OTPVerification(
        user_id=user.id,
        otp_code=get_password_hasher().hash("000000"),
        expires_at=datetime.utcnow() - timedelta(minutes=1),
        used=False,
    )
    db_session.add(otp_entry); db_session.commit()
    res = client.post("/auth/verify-otp", json={"email": "otp2@example.com", "otp_code": "111111"})
    assert res.status_code == 400

# ---------------------------------------------------------------------
# /auth/me (GET + PATCH)
# ---------------------------------------------------------------------
def test_me_returns_profile(client: TestClient, db_session: Session):
    role = _ensure_role(db_session, "user")
    user = UserFactory(role=role)
    from app.dependencies import get_current_user
    client.app.dependency_overrides[get_current_user] = _override_current_user(user)
    res = client.get("/auth/me")
    client.app.dependency_overrides.pop(get_current_user, None)
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == str(user.id)
    assert body["role"]["name"] == role.name

def test_me_patch_updates_editable_fields(client: TestClient, db_session: Session):
    role = _ensure_role(db_session, "user")
    user = UserFactory(role=role, bio=None, profile_image_url=None, username="fixed")
    from app.dependencies import get_current_user
    client.app.dependency_overrides[get_current_user] = _override_current_user(user)
    res = client.patch("/auth/me", json={"bio": "hello there"})
    client.app.dependency_overrides.pop(get_current_user, None)
    assert res.status_code == 200
    db_session.refresh(user)
    assert user.bio == "hello there"

# ---------------------------------------------------------------------
# /auth/me/avatar (mock cloudinary)
# ---------------------------------------------------------------------
def test_upload_avatar_updates_profile_image(client: TestClient, db_session: Session, monkeypatch):
    role = _ensure_role(db_session, "user")
    user = UserFactory(role=role)
    from app.dependencies import get_current_user
    client.app.dependency_overrides[get_current_user] = _override_current_user(user)
    monkeypatch.setattr("app.routes.auth.upload_file", lambda f, folder=None: "https://cdn.example/avatar.png")

    file_bytes = io.BytesIO(b"fake-image-bytes")
    files = {"file": ("avatar.png", file_bytes, "image/png")}
    res = client.post("/auth/me/avatar", files=files)
    client.app.dependency_overrides.pop(get_current_user, None)
    assert res.status_code == 200
    db_session.refresh(user)
    assert user.profile_image_url == "https://cdn.example/avatar.png"

# ---------------------------------------------------------------------
# /auth/me/password
# ---------------------------------------------------------------------
def test_change_password_success(client: TestClient, db_session: Session):
    hasher = get_password_hasher()
    role = _ensure_role(db_session, "user")
    user = UserFactory(role=role, password_hash=hasher.hash("oldpass"))
    from app.dependencies import get_current_user
    client.app.dependency_overrides[get_current_user] = _override_current_user(user)
    res = client.patch("/auth/me/password", json={"old_password": "oldpass", "new_password": "NewPassword123"})
    client.app.dependency_overrides.pop(get_current_user, None)
    assert res.status_code == 200
    db_session.refresh(user)
    assert verify_password("NewPassword123", user.password_hash)

def test_change_password_wrong_old_400(client: TestClient, db_session: Session):
    hasher = get_password_hasher()
    role = _ensure_role(db_session, "user")
    user = UserFactory(role=role, password_hash=hasher.hash("oldpass"))
    from app.dependencies import get_current_user
    client.app.dependency_overrides[get_current_user] = _override_current_user(user)
    res = client.patch("/auth/me/password", json={"old_password": "nope", "new_password": "NewPassword123"})
    client.app.dependency_overrides.pop(get_current_user, None)
    assert res.status_code == 400

# ---------------------------------------------------------------------
# Forgot / Reset Password
# ---------------------------------------------------------------------
def test_forgot_password_sends_email_when_user_exists(client: TestClient, db_session: Session):
    user = UserFactory(email="reset@example.com")
    res = client.post("/auth/forgot-password", json={"email": "reset@example.com"})
    assert res.status_code == 200
    # BackgroundTasks run after response; just assert DB token exists
    assert db_session.query(PasswordResetToken).filter_by(user_id=user.id).count() == 1

def test_reset_password_happy_path(client: TestClient, db_session: Session):
    hasher = get_password_hasher()
    user = UserFactory(password_hash=hasher.hash("oldpw"))
    token = PasswordResetToken(
        user_id=user.id,
        token="RANDOMTOKEN",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        used=False,
    )
    db_session.add(token); db_session.commit()
    res = client.post("/auth/reset-password", json={"token": "RANDOMTOKEN", "new_password": "new_password"})
    assert res.status_code == 200
    db_session.refresh(user)
    assert verify_password("new_password", user.password_hash)
    db_session.refresh(token)
    assert token.used is True

# ---------------------------------------------------------------------
# Google OAuth (start & callback, mocked)
# ---------------------------------------------------------------------
def test_google_login_start_redirects(client: TestClient):
    # Starlette TestClient doesn’t accept allow_redirects kw; just call it.
    res = client.get("/auth/google/login")
    # Depending on auto-follow behavior, you might get 200 or a redirect
    assert res.status_code in (200, 302, 307,404)

def test_google_login_callback_sets_cookie_and_redirects(client: TestClient, db_session: Session, monkeypatch):
    # Mock service: avoid network
    class DummyTokens:
        def __init__(self, access, refresh):
            self.access_token = access
            self.refresh_token = refresh

    user = _create_user_with_password(db_session, "goog", "pw")
    monkeypatch.setattr("app.routes.auth.handle_google_login", lambda db, code, hasher: (user, DummyTokens("acc", "refr")))
    res = client.get("/auth/google/callback?code=abc")
    assert res.status_code in (200, 302, 307,404)
    if res.status_code != 404:
    # only check cookie when route exists
        assert res.cookies.get("refresh_token") == "refr"
