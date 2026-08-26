"""Mailer's bounded retry and its hard total deadline.

/** WHY THESE EXIST: the SMTP send runs inline in the signup request. Two
    separate failure modes have to stay closed:

      1. A transient blip must not silently lose a verification email — under
         eager mode Celery's `autoretry_for` never fires, so `Mailer` is the only
         thing retrying (ADR 003).
      2. Those retries must not become the new hang. `task_time_limit` is
         unenforced without a worker and `smtplib` has no default socket
         timeout, so before this the only bound was Cloud Run's 300s service
         timeout — five minutes of a user waiting for a 504.

    The total budget is what reconciles them, and is the contract worth
    testing: worst-case wait is ONE number, not a number times an attempt
    count. **/
"""
import smtplib
import time

import pytest
from fastapi import HTTPException

from app.utils.email import Mailer

pytestmark = pytest.mark.unit


def _mailer(**kw):
    kw.setdefault("retry_delay", 0)      # don't really sleep through backoff
    kw.setdefault("timeout", 5)
    kw.setdefault("total_budget", 12)
    return Mailer(
        server="smtp.test", port=587, username="u", password="p",
        sender_email="noreply@test", sender_name="Quill", **kw
    )


def test_transient_failure_is_retried_and_can_succeed(monkeypatch):
    """A dropped connection on the first attempt must not lose the email.

    REGRESSION: before the in-process retry, `send_email` made exactly one
    attempt. Under eager mode nothing retried it, so a single transient blip —
    the most common SMTP failure — silently dropped a signup verification email
    while the request still returned 200.
    """
    attempts = []

    def flaky(self, to_email, msg, timeout):
        attempts.append(timeout)
        if len(attempts) == 1:
            raise smtplib.SMTPServerDisconnected("connection dropped")

    monkeypatch.setattr(Mailer, "_deliver", flaky)
    _mailer().send_email("a@test.com", "Verify", "<p>hi</p>")

    assert len(attempts) == 2, "should have retried once and then succeeded"


def test_gives_up_after_max_attempts_and_raises_502(monkeypatch):
    attempts = []

    def always_fails(self, to_email, msg, timeout):
        attempts.append(timeout)
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

    `smtplib.SMTPException` subclasses `OSError`, so a blanket handler would
    sweep these into the retry loop — hence the explicit PERMANENT_SMTP_ERRORS
    tuple. The send is inline, so every wasted attempt is a user waiting.
    """
    attempts = []

    def rejected(self, to_email, msg, timeout):
        attempts.append(timeout)
        raise error

    monkeypatch.setattr(Mailer, "_deliver", rejected)

    with pytest.raises(HTTPException) as exc:
        _mailer(max_attempts=3).send_email("a@test.com", "Verify", "<p>hi</p>")

    assert exc.value.status_code == 502
    assert len(attempts) == 1, f"{type(error).__name__} is permanent - must not retry"


def test_success_on_first_attempt_does_not_sleep(monkeypatch):
    attempts = []
    monkeypatch.setattr(Mailer, "_deliver",
                        lambda self, to, msg, timeout: attempts.append(timeout))
    monkeypatch.setattr("app.utils.email.time.sleep",
                        lambda _: (_ for _ in ()).throw(
                            AssertionError("must not sleep on first-attempt success")))

    _mailer().send_email("a@test.com", "Verify", "<p>hi</p>")
    assert len(attempts) == 1


# ---------------------------------------------------------------- the deadline

def test_per_attempt_timeout_is_passed_to_the_socket(monkeypatch):
    """The timeout must reach smtplib, or nothing is bounded at all."""
    seen = []
    monkeypatch.setattr(Mailer, "_deliver",
                        lambda self, to, msg, timeout: seen.append(timeout))

    _mailer(timeout=5, total_budget=12).send_email("a@test.com", "s", "b")
    assert seen == [5]


def test_total_budget_caps_the_whole_operation(monkeypatch):
    """A hanging provider must not cost more than the budget, however many
    attempts are configured.

    This is the bound that replaces the one eager mode took away. Without it,
    N attempts x a per-attempt timeout is the real worst case, and the user
    waits all of it inside their signup request.
    """
    now = {"t": 1000.0}
    monkeypatch.setattr("app.utils.email.time.monotonic", lambda: now["t"])
    monkeypatch.setattr("app.utils.email.time.sleep",
                        lambda s: now.__setitem__("t", now["t"] + s))

    attempts = []

    def hangs_for_its_whole_timeout(self, to_email, msg, timeout):
        attempts.append(timeout)
        now["t"] += timeout          # simulate burning the full socket timeout
        raise TimeoutError("provider hung")

    monkeypatch.setattr(Mailer, "_deliver", hangs_for_its_whole_timeout)

    start = now["t"]
    with pytest.raises(HTTPException):
        # 10 attempts x 5s would be 50s if the budget weren't enforced.
        _mailer(timeout=5, total_budget=12, max_attempts=10,
                retry_delay=1).send_email("a@test.com", "s", "b")

    elapsed = now["t"] - start
    assert elapsed <= 12, f"budget blown: {elapsed}s of a 12s budget"
    assert len(attempts) < 10, "should stop when the budget runs out, not at max_attempts"


def test_last_attempt_is_shortened_to_fit_the_budget(monkeypatch):
    """An attempt is never given more time than the budget has left."""
    now = {"t": 500.0}
    monkeypatch.setattr("app.utils.email.time.monotonic", lambda: now["t"])
    monkeypatch.setattr("app.utils.email.time.sleep",
                        lambda s: now.__setitem__("t", now["t"] + s))

    seen = []

    def burn(self, to_email, msg, timeout):
        seen.append(timeout)
        now["t"] += timeout
        raise TimeoutError("hung")

    monkeypatch.setattr(Mailer, "_deliver", burn)

    with pytest.raises(HTTPException):
        _mailer(timeout=5, total_budget=7, max_attempts=5,
                retry_delay=0).send_email("a@test.com", "s", "b")

    assert seen[0] == 5
    assert seen[-1] <= 2, f"last attempt should be clipped to the remainder, got {seen[-1]}"
    assert sum(seen) <= 7
