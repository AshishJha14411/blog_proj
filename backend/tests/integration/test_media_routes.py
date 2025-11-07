# tests/integration/test_media_routes.py
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user

pytestmark = pytest.mark.integration


def _override_user(user):
    return lambda: user


def _fake_image_bytes() -> bytes:
    # Tiny “PNG” header-ish bytes; any bytes are fine for the TestClient
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def test_media_upload_requires_auth_401(client: TestClient):
    files = {"file": ("pic.png", _fake_image_bytes(), "image/png")}
    res = client.post("/media/upload", files=files)
    assert res.status_code == 401


def test_media_upload_success_returns_url_and_uses_user_folder(
    client: TestClient, db_session: Session, monkeypatch
):
    from tests.factories import UserFactory
    user = UserFactory()

    # Override auth
    client.app.dependency_overrides[get_current_user] = _override_user(user)

    # Capture arguments passed to the underlying uploader used by the service
    captured = {}

    def fake_upload_file(file_like, folder: str = "") -> str:
        # Assert we’re using the expected folder
        assert folder == f"users/{user.id}"
        # Capture for extra assertions if we want
        captured["folder"] = folder
        captured["file_read_peek"] = file_like.read(8)
        file_like.seek(0)
        # Return a believable Cloudinary URL
        return f"https://res.cloudinary.com/demo/image/upload/v123/{folder}/abc.png"

    # Patch the import that the service uses
    monkeypatch.setattr("app.services.media.upload_file", fake_upload_file)

    files = {"file": ("pic.png", io.BytesIO(_fake_image_bytes()), "image/png")}
    res = client.post("/media/upload", files=files)

    # Cleanup overrides
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 201, res.text
    body = res.json()
    assert "url" in body
    assert body["url"].startswith("https://res.cloudinary.com/demo/image/upload")
    assert f"users/{user.id}" in body["url"]
    # sanity on our capture
    assert captured["folder"] == f"users/{user.id}"
    assert isinstance(captured["file_read_peek"], (bytes, bytearray))


def test_media_upload_handles_cloudinary_error_500(
    client: TestClient, db_session: Session, monkeypatch
):
    from tests.factories import UserFactory
    user = UserFactory()

    client.app.dependency_overrides[get_current_user] = _override_user(user)

    def fake_upload_file_raises(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.services.media.upload_file", fake_upload_file_raises)

    files = {"file": ("bad.png", io.BytesIO(_fake_image_bytes()), "image/png")}
    res = client.post("/media/upload", files=files)

    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 500
    assert res.json().get("detail") == "Image upload failed"
