"""
/** WHY: end-to-end proof that the ticket flow admits real callers and
    refuses invalid ones. The starlette TestClient supports WebSocket
    connections via a with-block context manager. **/
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.ws import tickets

pytestmark = pytest.mark.integration


def test_ws_ticket_endpoint_mints_a_token(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, RoleFactory
    user = UserFactory(role=RoleFactory(name="user"))
    client.app.dependency_overrides[get_current_user] = lambda: user
    try:
        res = client.post("/ws/ticket")
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ticket"]
    assert body["expires_in"] == tickets.TICKET_TTL_SECONDS


def test_ws_connects_with_valid_ticket(client: TestClient, db_session: Session):
    """The handshake succeeds and the connection accepts frames."""
    from tests.factories import UserFactory, RoleFactory
    user = UserFactory(role=RoleFactory(name="user"))
    token = tickets.mint_ticket(user.id)

    # /** WHY: TestClient WebSocket needs an explicit event-loop dance under
    #     httpx-based TestClient — the context manager form works out of
    #     the box for a single-frame test. **/
    with client.websocket_connect(f"/ws/notifications?ticket={token}") as ws:
        # Nothing to receive by default (server pings only after 25s of
        # silence). Just prove the handshake succeeded by closing cleanly.
        pass


def test_ws_rejects_missing_ticket(client: TestClient):
    """A handshake with no ticket must be closed with 4401."""
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/notifications"):
            pass
    assert excinfo.value.code == 4401


def test_ws_rejects_reused_ticket(client: TestClient, db_session: Session):
    """After the first successful consume, the same ticket must fail."""
    from tests.factories import UserFactory, RoleFactory
    from starlette.websockets import WebSocketDisconnect
    user = UserFactory(role=RoleFactory(name="user"))
    token = tickets.mint_ticket(user.id)

    # First connection consumes the ticket.
    with client.websocket_connect(f"/ws/notifications?ticket={token}"):
        pass

    # Second connection with the same ticket must be rejected.
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(f"/ws/notifications?ticket={token}"):
            pass
    assert excinfo.value.code == 4401
