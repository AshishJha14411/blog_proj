"""
/** WHY: HTTP endpoints for the WS lifecycle (mint ticket, upgrade to WS).
    Keeps the ticket + socket routes together instead of scattering across
    routes/*.py. **/
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, status

from app.dependencies import get_current_user
from app.models.user import User
from app.utils.rate_limiter import rate_limit
from app.ws import tickets
from app.ws.manager import manager

logger = logging.getLogger(__name__)

# /ws prefix so nginx/router can route WS traffic separately if needed.
router = APIRouter(prefix="/ws", tags=["WebSocket"])


# recommended by claude opus 4.7: keep the ticket endpoint rate-limited on
# top of auth. Cheap for a real client (one mint per WS lifecycle) and
# stops a script from burning tickets to keep Redis busy.
def _ticket_rate_limit(request: Request):
    # 20 tickets/min per user is plenty for a normal client that reconnects
    # on backoff. Adjust upward if the frontend hook proves this too tight.
    rate_limit(request, limit=20, window=60, scope="ws:ticket")


@router.post("/ticket", status_code=status.HTTP_200_OK)
def create_ticket(
    request: Request,
    _rl: None = Depends(_ticket_rate_limit),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    /** WHAT: mint a single-use, 30-second ticket the client will present on
        the /ws/notifications handshake. Client should ask for a fresh
        ticket on every reconnect. **/
    """
    token = tickets.mint_ticket(current_user.id)
    return {"ticket": token, "expires_in": tickets.TICKET_TTL_SECONDS}


# recommended by claude opus 4.7: use 4401 (subprotocol level, WS-specific)
# for auth failures. 1008 (policy violation) also works but doesn't clearly
# signal "auth" to a client that speaks the pattern.
WS_AUTH_CLOSE = 4401


@router.websocket("/notifications")
async def ws_notifications(ws: WebSocket, ticket: str | None = None) -> None:
    """
    /** WHAT: accept the WS handshake, redeem the ticket, join the user to
        the ConnectionManager, then loop until disconnect. **/
    /** WHY-THIS-WAY: the handshake happens BEFORE `accept()` runs, so we
        redeem the ticket up-front. If the ticket is bad we call
        `close(WS_AUTH_CLOSE)` before accepting — the client sees a clean
        auth error, not a mystery disconnect. **/
    """
    user_id = tickets.consume_ticket(ticket) if ticket else None
    if not user_id:
        # Refuse the upgrade. `close` before `accept` sends 401 to the client.
        await ws.close(code=WS_AUTH_CLOSE)
        return

    await manager.connect(user_id, ws)
    try:
        # /** WHY: server-driven ping every 25s. Idle connections through
        #     load balancers get reaped at ~60s; the ping keeps them alive
        #     AND acts as a liveness probe on our side. **/
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=25)
            except asyncio.TimeoutError:
                # Send a lightweight heartbeat frame the client can ignore.
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("ws_notifications: unexpected error for %s: %s", user_id, exc)
    finally:
        await manager.disconnect(user_id, ws)
