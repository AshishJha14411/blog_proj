"""
/** WHY: full-stack WS check for the support chatbot: ticket auth,
    streaming, budget cap, and escalation. **/
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.support import routes as support_routes
from app.support import session as chat_session
from app.ws import tickets

pytestmark = pytest.mark.integration


def _mint(user):
    return tickets.mint_ticket(user.id)


def test_support_rejects_missing_ticket(client: TestClient):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/support"):
            pass
    assert excinfo.value.code == 4401


def test_support_streams_deltas_and_ends_with_done(client: TestClient, db_session: Session, monkeypatch):
    """A user message triggers streaming; server sends deltas then done."""
    from tests.factories import UserFactory, RoleFactory
    user = UserFactory(role=RoleFactory(name="user"))
    token = _mint(user)

    # Replace the LLM streamer with a deterministic 3-chunk generator.
    def fake_stream(prompt):
        yield "Hello, "
        yield "how "
        yield "can I help?"

    monkeypatch.setattr(support_routes._llm, "generate_stream", fake_stream)
    monkeypatch.setattr(support_routes, "moderate_content", lambda _: (False, []))

    with client.websocket_connect(f"/ws/support?ticket={token}") as ws:
        ws.send_json({"type": "user", "content": "hi"})
        frames = []
        while True:
            frame = ws.receive_json()
            if frame.get("type") == "ping":
                continue
            frames.append(frame)
            if frame.get("type") in ("done", "error", "budget_exceeded"):
                break

    types = [f["type"] for f in frames]
    assert "delta" in types
    assert types[-1] == "done"
    combined = "".join(f["text"] for f in frames if f["type"] == "delta")
    assert combined == "Hello, how can I help?"


def test_support_refuses_over_budget(client: TestClient, db_session: Session, monkeypatch):
    """If the user is at their daily cap, the server sends budget_exceeded."""
    from tests.factories import UserFactory, RoleFactory
    user = UserFactory(role=RoleFactory(name="user"))
    token = _mint(user)

    monkeypatch.setattr(support_routes, "moderate_content", lambda _: (False, []))

    # Exhaust the budget before opening the socket.
    for _ in range(chat_session.DAILY_MESSAGE_BUDGET):
        chat_session.claim_budget(str(user.id))

    with client.websocket_connect(f"/ws/support?ticket={token}") as ws:
        ws.send_json({"type": "user", "content": "hi"})
        frame = ws.receive_json()
        while frame.get("type") == "ping":
            frame = ws.receive_json()
        assert frame["type"] == "budget_exceeded"


def test_support_escalate_enqueues_ticket_task(client: TestClient, db_session: Session, monkeypatch):
    """Escalate frame should trigger the create_support_ticket_task path."""
    from tests.factories import UserFactory, RoleFactory
    user = UserFactory(role=RoleFactory(name="user"))
    token = _mint(user)

    calls: list[dict] = []
    class _StubTask:
        def delay(self, **kwargs):
            calls.append(kwargs)
    monkeypatch.setattr(support_routes, "create_support_ticket_task", _StubTask())

    with client.websocket_connect(f"/ws/support?ticket={token}") as ws:
        ws.send_json({"type": "escalate", "reason": "need a human"})
        frame = ws.receive_json()
        while frame.get("type") == "ping":
            frame = ws.receive_json()
        assert frame["type"] == "escalated"

    assert len(calls) == 1
    assert calls[0]["reason"] == "need a human"
    assert calls[0]["user_id"] == str(user.id)


def test_support_flags_bad_input(client: TestClient, db_session: Session, monkeypatch):
    """Input caught by content moderation gets an error frame, not an LLM call."""
    from tests.factories import UserFactory, RoleFactory
    user = UserFactory(role=RoleFactory(name="user"))
    token = _mint(user)

    monkeypatch.setattr(support_routes, "moderate_content", lambda _: (True, ["profanity"]))
    # Set a boom-if-called stub so we prove moderation blocked before LLM.
    def _forbidden(*_a, **_k):
        raise AssertionError("LLM must not be called when moderation flags input")
    monkeypatch.setattr(support_routes._llm, "generate_stream", _forbidden)

    with client.websocket_connect(f"/ws/support?ticket={token}") as ws:
        ws.send_json({"type": "user", "content": "toxic prompt"})
        frame = ws.receive_json()
        while frame.get("type") == "ping":
            frame = ws.receive_json()
        assert frame["type"] == "error"
