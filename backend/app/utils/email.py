import logging
import smtplib
import time
from email.mime.text import MIMEText
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# /** WHY these are singled out: `smtplib.SMTPException` subclasses `OSError`,
#     so a blanket `except OSError` swallows permanent failures too. Retrying
#     any of these is pure latency — a rejected recipient stays rejected and bad
#     credentials stay bad — and every retry is time the signup request is
#     blocked on. They short-circuit to a 502 immediately. **/
PERMANENT_SMTP_ERRORS = (
    smtplib.SMTPAuthenticationError,   # wrong credentials
    smtplib.SMTPRecipientsRefused,     # bad destination address
    smtplib.SMTPSenderRefused,         # sender not allowed by the relay
    smtplib.SMTPNotSupportedError,     # server can't do what we asked
)


class Mailer:
    """SMTP sender with a small, bounded retry.

    /** WHY THE RETRY LIVES HERE AND NOT IN CELERY: `send_email_task` is
        configured with `autoretry_for` + exponential backoff, but production
        runs `task_always_eager=True` (there is no worker — see
        docs/adr/001-workerless-inline-tasks.md). Eager mode does NOT perform
        retries: `self.retry()` raises rather than re-running. So that entire
        retry curve is inert in production, and a single transient SMTP blip
        silently lost a signup verification email with no error shown to the
        user.

        A couple of in-process attempts recover the common case — a dropped
        connection or a momentary greylist — at zero infrastructure cost, and
        they work identically with or without a worker.

        Deliberately NOT a substitute for durable retries: this cannot survive
        a sustained outage or a process restart. See ADR 003. **/
    """

    def __init__(
        self,
        server: str,
        port: int,
        username: str,
        password: str,
        sender_email: str,
        sender_name: str,
        timeout: float = 10.0,
        max_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.timeout = timeout
        # 3 attempts with a 1s linear backoff = at most ~3s added to the
        # request. Chosen against signup latency: the send happens inline, so
        # every extra attempt is time the user waits on the response.
        self.max_attempts = max(1, max_attempts)
        self.retry_delay = retry_delay

    def _deliver(self, to_email: str, msg: MIMEText) -> None:
        # `timeout` prevents a slow/hung SMTP server from wedging the caller.
        with smtplib.SMTP(self.server, self.port, timeout=self.timeout) as smtp:
            smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.sendmail(self.sender_email, [to_email], msg.as_string())

    def send_email(self, to_email: str, subject: str, body: str):
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.sender_email}>"
        msg["To"] = to_email

        for attempt in range(1, self.max_attempts + 1):
            try:
                self._deliver(to_email, msg)
                if attempt > 1:
                    logger.info(
                        "SMTP send succeeded on attempt %s/%s (subject=%r)",
                        attempt, self.max_attempts, subject,
                    )
                return
            except PERMANENT_SMTP_ERRORS:
                logger.exception(
                    "SMTP send permanently rejected (subject=%r) - not retrying", subject
                )
                break
            except (smtplib.SMTPException, OSError, TimeoutError):
                last = attempt == self.max_attempts
                logger.warning(
                    "SMTP send failed (attempt %s/%s, subject=%r)%s",
                    attempt, self.max_attempts, subject,
                    "" if last else " - retrying",
                    exc_info=True,
                )
                if last:
                    break
                # Linear, not exponential: the whole budget is ~3s, so an
                # exponential curve would spend it all on one long sleep.
                time.sleep(self.retry_delay * attempt)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Email service is temporarily unavailable.",
        )
