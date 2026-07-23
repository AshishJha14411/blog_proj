"""
/** WHY: when the bot escalates a conversation to a human, we need to
    (a) persist a ticket, (b) notify moderators via WS/email, and (c) do
    it durably so an app restart between "user said escalate" and
    "moderators saw it" doesn't lose the request. **/

/** WHAT: `create_support_ticket_task(session_id, user_id, transcript)`
    writes a row + notifies moderators. Runs asynchronously so the chat
    UX doesn't stall on the DB write. **/
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import String
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.notifications import notify
from app.utils.idempotency import claim_once, release
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.support.create_support_ticket_task",
    bind=True,
    max_retries=2,
    retry_backoff=5,
    retry_backoff_max=30,
    retry_jitter=True,
)
def create_support_ticket_task(
    self,
    *,
    session_id: str,
    user_id: str | None,
    transcript: list[dict],
    reason: str = "escalated",
) -> dict:
    """
    /** WHAT: build a ticket record from the chat transcript and notify
        every moderator so someone picks it up. Returns the ticket id. **/

    /** WHY-THIS-WAY: idempotency by session_id so a redelivered escalate
        (double-click on the button, Celery retry after ACK loss) doesn't
        spam moderators with duplicates. **/
    """
    dedupe = f"support_ticket:{session_id}"
    if not claim_once(dedupe):
        logger.info("support ticket already created for session %s", session_id)
        return {"status": "duplicate", "session_id": session_id}

    db: Session = SessionLocal()
    try:
        # recommended by claude opus 4.7: keep the ticket schema minimal.
        # If you outgrow this, add a dedicated table + Pydantic schema.
        # For now the AuditLog table already has `before_state`/`after_state`
        # JSON columns that fit this purpose (transcript in after_state).
        from app.models.audit_log import AuditLog
        actor_uuid = uuid.UUID(user_id) if user_id else None
        row = AuditLog(
            actor_user_id=actor_uuid,
            action="support_ticket_created",
            target_type="chat_session",
            target_id=session_id,
            after_state={"reason": reason, "transcript": transcript[-30:]},
        )
        db.add(row)
        db.commit()

        # Notify every moderator + superadmin.
        from app.models.role import Role
        from app.models.user import User
        mods = (
            db.query(User)
            .join(Role, Role.id == User.role_id)
            .filter(Role.name.in_(("moderator", "superadmin")), User.is_disabled.is_(False))
            .all()
        )
        for mod in mods:
            notify(
                db,
                recipient_id=mod.id,
                action="support_escalated",
                actor_id=actor_uuid,
                target_type="chat_session",
                target_id=None,  # session_id is a string; AuditLog carries the ref
            )

        return {"status": "created", "session_id": session_id, "notified": len(mods)}
    except Exception:
        release(dedupe)
        db.rollback()
        raise
    finally:
        db.close()
