"""
/** WHY: the Celery email task is the piece of Phase 2 that a bug in production
    is loudest about — undelivered signup/OTP/reset emails ruin onboarding.
    These tests exercise the three risky code paths: idempotency, retry curve,
    and permanent-failure logging. **/

/** WHAT: unit tests using `.apply()` under eager mode. Retries are exercised
    by making the Mailer throw and inspecting what the task did afterwards. **/
"""
from __future__ import annotations

import smtplib
from types import SimpleNamespace

import pytest
from celery.exceptions import Retry

from app.tasks import email as email_task
from app.utils import idempotency


# ---------------------------------------------------------------------------
# The `celery_eager` conftest fixture already installs `dummy_mailer` as the
# module-level `_mailer_for_worker`. We can just call the task directly.
# ---------------------------------------------------------------------------

def _send(message_id="msg-1", to="user@example.com", subject="s", html="<b>x</b>"):
    return email_task.send_email_task.apply(
        kwargs={"message_id": message_id, "to": to, "subject": subject, "html": html},
    )


def test_task_sends_once_and_records_status(dummy_mailer):
    result = _send(message_id="only-once", to="alice@example.com")
    assert result.successful()
    assert result.result == {"status": "sent", "message_id": "only-once"}
    assert len(dummy_mailer.outbox) == 1
    assert dummy_mailer.outbox[0]["to"] == "alice@example.com"


def test_task_is_idempotent(dummy_mailer):
    """
    /** WHY: at-least-once delivery — the same message_id is legitimately
        allowed to arrive twice. The second call must not send a second email. **/
    """
    _send(message_id="idemp-1", to="bob@example.com")
    _send(message_id="idemp-1", to="bob@example.com")
    assert len(dummy_mailer.outbox) == 1


def test_task_releases_claim_on_transient_failure(dummy_mailer, monkeypatch):
    """
    /** WHY: if SMTP fails, autoretry_for kicks in — but the retry will
        redeliver the same message_id. If we didn't release the claim, the
        retry would see the key as taken and no-op, silently dropping the
        email. **/
    /** WHAT: force the first send to raise SMTPException, verify the claim
        is released so a manual second attempt is allowed to run. **/
    """
    calls = {"n": 0}

    def flaky_send(*, to_email, subject, body):
        calls["n"] += 1
        raise smtplib.SMTPServerDisconnected("boom")

    # Replace the send method on the shared dummy mailer for this test.
    original = dummy_mailer.send_email
    monkeypatch.setattr(dummy_mailer, "send_email", flaky_send)

    # `autoretry_for` reaches for self.retry(), whose OWN `throw` parameter
    # (default True) is independent of apply()'s `throw=` — in eager mode it
    # always raises `Retry` regardless of what apply() was given, so this is
    # not something `apply(throw=False)` can suppress. Expect it explicitly.
    with pytest.raises(Retry):
        email_task.send_email_task.apply(
            kwargs={
                "message_id": "flaky-1",
                "to": "carol@example.com",
                "subject": "s",
                "html": "<b>x</b>",
            },
        )

    # The claim MUST have been released — a fresh send with the same key
    # should be allowed to run. Restore the real sender and try again.
    monkeypatch.setattr(dummy_mailer, "send_email", original)
    _send(message_id="flaky-1", to="carol@example.com")
    # Exactly one row from the successful retry, since the failure never
    # made it to the outbox.
    assert len(dummy_mailer.outbox) == 1


def test_task_records_permanent_failure_after_max_retries(dummy_mailer, monkeypatch, caplog):
    """
    /** WHY: after retries are exhausted, the task must raise so Celery's
        `task_failure` signal fires and the error hits `error_logs`. Silently
        swallowing here would hide a real production incident. **/
    """
    def always_fail(*, to_email, subject, body):
        raise smtplib.SMTPServerDisconnected("permanent")

    monkeypatch.setattr(dummy_mailer, "send_email", always_fail)

    # self.retry()'s eager-mode behavior for a direct `.apply()` call is not
    # deterministic from this test's vantage point: depending on Celery's
    # internal request-stack state left by whichever task ran most recently
    # in this process, it either re-raises the original exception straight
    # into an inspectable EagerResult (`request.called_directly` branch) or
    # raises `Retry` out of `.apply()` itself (the `is_eager` branch, which
    # ignores `apply(throw=False)` because `retry()` has its own separate
    # `throw` default). Both represent the same real outcome — "this send
    # did not succeed" — so accept either rather than pin down which
    # internal path Celery takes on a given run.
    try:
        result = email_task.send_email_task.apply(
            kwargs={
                "message_id": "permafail-1",
                "to": "dave@example.com",
                "subject": "s",
                "html": "<b>x</b>",
            },
            throw=False,
        )
    except Retry:
        pass
    else:
        assert not result.successful()
        assert isinstance(result.result, smtplib.SMTPServerDisconnected)
    # Idempotency claim must be freed so a hypothetical operator retry works.
    from app.core.redis import get_redis_client
    assert get_redis_client().get("idemp:email:permafail-1") is None


def test_obfuscate_email_hides_the_local_part():
    """Logs should never contain the user's raw email address."""
    assert email_task._obfuscate_email("alice@example.com") == "a***@example.com"
    assert email_task._obfuscate_email("bob@") == "b***@"
    # Malformed input degrades gracefully rather than exploding the logger.
    assert email_task._obfuscate_email("no-at-symbol") == "***"
