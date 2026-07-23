"""
/** WHY: chat widget lives on the frontend. Backend gets a WS endpoint that
    (a) authenticates via a one-time ticket (same pattern as notifications),
    (b) persists history in Redis, (c) streams LLM output, (d) enforces
    daily message budget, (e) escalates to a human on request. **/

/** WHAT: `/ws/support?ticket=…`. Frames the client can send:
      { "type": "user", "content": "..." }         normal message
      { "type": "escalate", "reason": "..." }      hand off to a human
    Frames the server sends:
      { "type": "delta", "text": "..." }           streaming chunk
      { "type": "done" }                           end of assistant reply
      { "type": "budget_exceeded" }                over daily cap
      { "type": "escalated", "ticket": "..." }     escalation confirmed
      { "type": "error", "message": "..." }        anything unexpected **/
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Iterable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.llm.adapter import LLMAdapter, LLMError
from app.services.moderation import moderate_content
from app.support import kb, session as chat_session
from app.tasks.support import create_support_ticket_task
from app.ws import tickets
from app.ws.routes import WS_AUTH_CLOSE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Support"])

# Reuse the same adapter singleton the story service already has.
_llm = LLMAdapter()


def _build_prompt(user_message: str, history: Iterable[dict]) -> str:
    """
    /** WHY: single string prompt so both providers accept it. The system
        prompt is the KB + role instructions; conversation history is a
        transcript-style prefix. **/
    /** WHY-THIS-WAY: naïve concatenation, not a chat-format template — the
        adapter is provider-agnostic and can't rely on chat-role support
        being available on every backend. **/
    """
    kb_text = kb.get_kb_text()
    lines: list[str] = []
    if kb_text:
        lines.append("KNOWLEDGE BASE:\n" + kb_text.strip())
    lines.append(
        "You are Quill & Code support. Answer clearly. "
        "If the request needs account changes or you don't know, "
        "tell the user you can escalate to a human."
    )
    lines.append("---")
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        prefix = "USER" if role == "user" else "ASSISTANT"
        lines.append(f"{prefix}: {content}")
    lines.append(f"USER: {user_message}")
    lines.append("ASSISTANT:")
    return "\n\n".join(lines)


async def _stream_reply(ws: WebSocket, prompt: str, session_id: str) -> str:
    """
    /** WHAT: run the streaming LLM in a thread (the adapter is sync) and
        relay chunks over the WS as they arrive. Returns the full text so
        the caller can persist it. **/
    /** WHY-THIS-WAY: run_in_executor keeps the event loop responsive —
        blocking on a sync generator would freeze other tabs / pings. **/
    """
    loop = asyncio.get_running_loop()
    stream = await loop.run_in_executor(None, lambda: _llm.generate_stream(prompt))
    collected: list[str] = []
    # Consume the sync iterator on a thread so we don't block the event loop.
    def _next_chunk(it):
        try:
            return next(it)
        except StopIteration:
            return None

    it = iter(stream)
    while True:
        chunk = await loop.run_in_executor(None, _next_chunk, it)
        if chunk is None:
            break
        collected.append(chunk)
        await ws.send_json({"type": "delta", "text": chunk})
    return "".join(collected)


@router.websocket("/support")
async def ws_support(ws: WebSocket, ticket: str | None = None) -> None:
    """
    /** WHY: one endpoint, everything the chat widget needs. **/
    /** WHY-THIS-WAY: the same ticket pattern as notifications so a stolen
        auth cookie can't be replayed straight into a paid LLM channel. **/
    """
    user_id = tickets.consume_ticket(ticket) if ticket else None
    if not user_id:
        # Anonymous chat could be enabled later with a guest:{uuid} identity
        # + tighter budget. For now, gate the whole endpoint on auth.
        await ws.close(code=WS_AUTH_CLOSE)
        return

    await ws.accept()
    # /** WHY: one session per socket. Reconnects rebuild history from
    #     Redis under the same id if the client reuses it. **/
    session_id = f"user:{user_id}"

    try:
        while True:
            try:
                frame = await asyncio.wait_for(ws.receive_json(), timeout=60)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping"})
                continue
            except WebSocketDisconnect:
                break

            frame_type = (frame or {}).get("type")
            if frame_type == "escalate":
                # /** WHAT: enqueue a Celery task with the transcript and
                #     confirm to the client. The task notifies moderators. **/
                history = chat_session.get_history(session_id)
                create_support_ticket_task.delay(
                    session_id=session_id,
                    user_id=user_id,
                    transcript=history,
                    reason=(frame.get("reason") or "user_requested")[:200],
                )
                await ws.send_json({"type": "escalated", "ticket": session_id})
                continue

            if frame_type != "user":
                await ws.send_json({"type": "error", "message": "Unknown frame type."})
                continue

            content = (frame.get("content") or "").strip()
            if not content:
                continue
            if len(content) > 4000:
                # /** WHY: schema-level length cap. LLM cost is proportional
                #     to input length; a 500KB message is either a mistake
                #     or abuse. **/
                await ws.send_json({"type": "error", "message": "Message too long."})
                continue

            # Guardrail 1: user input moderation.
            flagged, _cats = moderate_content([content])
            if flagged:
                await ws.send_json({
                    "type": "error",
                    "message": "That message tripped our content filter. Rephrase or escalate.",
                })
                continue

            # Guardrail 2: per-day budget.
            if not chat_session.claim_budget(user_id):
                await ws.send_json({"type": "budget_exceeded"})
                continue

            # Persist the user's message before we call the LLM so a crash
            # doesn't lose the transcript. Assistant reply is appended after
            # streaming completes.
            chat_session.append_message(session_id, "user", content)
            history = chat_session.get_history(session_id)

            prompt = _build_prompt(content, history[:-1])  # exclude the just-added user msg from prompt duplication
            try:
                full_text = await _stream_reply(ws, prompt, session_id)
            except LLMError as exc:
                logger.warning("ws_support: LLM error: %s", exc)
                await ws.send_json({"type": "error", "message": "The assistant is unavailable."})
                continue

            chat_session.append_message(session_id, "assistant", full_text)
            await ws.send_json({"type": "done", "message_id": str(uuid.uuid4())})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        logger.exception("ws_support: unhandled error: %s", exc)
        try:
            await ws.send_json({"type": "error", "message": "Internal server error."})
        except Exception:
            pass
