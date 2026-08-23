"""Mailer's bounded in-process retry.

/** WHY THESE EXIST: production runs Celery in eager mode (no worker), where
    `autoretry_for` never fires — so `Mailer` is the ONLY thing standing between
    a transient SMTP blip and a silently lost signup email. That makes this
    retry load-bearing, and worth testing at the boundary rather than trusting
    the config on the task. **/
"""
import smtplib

import pytest
from fastapi import HTTPException

from app.utils.email import Mailer

pytestmark = pytest.mark.unit


def _mailer(**kw):
    # retry_delay=0 so the suite doesn't actually sleep through the backoff.
    kw.setdefault("retry_delay", 0)
    return Mailer(
        server="smtp.test", port=587, username="u", password="p",
        sender_email="noreply@test", sender_name="Quill", **kw
    )


def test_transient_failure_is_retried_and_can_succeed(monkeypatch):
    """A dropped connection on the first attempt must not lose the email.

    REGRESSION: before the in-process retry, `send_email` made exactly one
    attempt. Under eager mode nothing retried it, so this scenario — a single
    transient blip, the overwhelmingly common SMTP failure — silently dropped
    a signup verification email while the request still returned 200.
    """
    attempts = []

    def flaky(self, to_email, msg):
        attempts.append(to_email)
        if len(attempts) == 1:
            raise smtplib.SMTPServerDisconnected("connection dropped")

    monkeypatch.setattr(Mailer, "_deliver", flaky)

    _mailer().send_email("a@test.com", "Verify", "<p>hi</p>")

    assert len(attempts) == 2, "should have retried once and then succeeded"


def test_gives_up_after_max_attempts_and_raises_502(monkeypatch):
    attempts = []

    def always_fails(self, to_email, msg):
        attempts.append(to_email)
        raise smtplib.SMTPServerDisconnected("still down")

    monkeypatch.setattr(Mailer, "_deliver", always_fails)

    with pytest.raises(HTTPException) as exc:
        _mailer(max_attempts=3).send_email("a@test.com", "Verify", "<p>hi</p>")

    assert exc.value.status_code == 502
    assert len(attempts) == 3, "bounded — must not retry forever"


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPRecipientsRefused({}),
        smtplib.SMTPAuthenticationError(535, b"bad credentials"),
        smtplib.SMTPSenderRefused(550, b"denied", "noreply@test"),
    ],
)
def test_permanent_failures_are_not_retried(monkeypatch, error):
    """Retrying a rejected recipient or bad credentials is pure added latency.

    This matters more than usual here: the send is inline, so every wasted
    attempt is time the signup request blocks. `smtplib.SMTPException` subclasses
    `OSError`, so a blanket handler would sweep these in — hence the explicit
    PERMANENT_SMTP_ERRORS tuple.
    """
    attempts = []

    def rejected(self, to_email, msg):
        attempts.append(to_email)
        raise error

    monkeypatch.setattr(Mailer, "_deliver", rejected)

    with pytest.raises(HTTPException) as exc:
        _mailer(max_attempts=3).send_email("a@test.com", "Verify", "<p>hi</p>")

    assert exc.value.status_code == 502
    assert len(attempts) == 1, f"{type(error).__name__} is permanent - must not retry"


def test_success_on_first_attempt_does_not_sleep(monkeypatch):
    attempts = []
    monkeypatch.setattr(Mailer, "_deliver", lambda self, to, msg: attempts.append(to))

    def explode(_):
        raise AssertionError("must not sleep when the first attempt succeeds")

    monkeypatch.setattr("app.utils.email.time.sleep", explode)

    _mailer().send_email("a@test.com", "Verify", "<p>hi</p>")
    assert len(attempts) == 1
