import logging
import smtplib
import time
from email.mime.text import MIMEText
from typing import Optional

from fastapi import HTTPException, status

from app.core.config import settings

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
    """SMTP sender bounded by a hard total deadline.

    /** WHY THIS IS BOUNDED AT ALL: the send runs INLINE in the request that
        triggered it — production has no Celery worker (ADR 001), and
        `task_time_limit` is enforced *by a worker*, so under eager mode it is
        not enforced at all. `smtplib` has no default socket timeout either: it
        inherits the global default of `None` and blocks until the OS gives up.

        The two together meant a hung mail provider held the signup request
        until Cloud Run's 300s service timeout fired — the user waiting the full
        five minutes for a 504, on a request whose account row had already been
        committed successfully. **/

    /** WHY A TOTAL BUDGET AND NOT JUST A PER-ATTEMPT TIMEOUT: a per-attempt
        timeout alone still multiplies. Three attempts at 10s with backoff is 33
        seconds of blocking, which is a worse promise than the single 10s call it
        replaced. `total_budget` is therefore the real contract: it caps every
        attempt AND the sleeps between them, so the worst case a user can wait on
        signup because of email is one number, not a number times a count.

        The retry survives because it earns its place — a single transient blip
        is the common SMTP failure and silently lost a verification email before
        (ADR 003). It just isn't allowed to cost unbounded time. **/
    """

    def __init__(
        self,
        server: str,
        port: int,
        username: str,
        password: str,
        sender_email: str,
        sender_name: str,
        timeout: Optional[float] = None,
        total_budget: Optional[float] = None,
        max_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.sender_name = sender_name
        # Default from settings so both are tunable by env without a redeploy;
        # explicit args still win, which is what the tests use.
        self.timeout = settings.SMTP_TIMEOUT_SECONDS if timeout is None else timeout
        self.total_budget = (
            settings.SMTP_TOTAL_BUDGET_SECONDS if total_budget is None else total_budget
        )
        self.max_attempts = max(1, max_attempts)
        self.retry_delay = retry_delay

    def _deliver(self, to_email: str, msg: MIMEText, timeout: float) -> None:
        # /** The timeout belongs on the CONSTRUCTOR, not the individual calls:
        #     smtplib applies it to the underlying socket, so it bounds the
        #     connect AND every command on that connection. A connect-only
        #     timeout wouldn't help against a provider that accepts the
        #     connection and then stalls mid-DATA. **/
        with smtplib.SMTP(self.server, self.port, timeout=timeout) as smtp:
            smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.sendmail(self.sender_email, [to_email], msg.as_string())

    def send_email(self, to_email: str, subject: str, body: str):
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.sender_email}>"
        msg["To"] = to_email

        # monotonic, not time(): immune to wall-clock adjustments.
        deadline = time.monotonic() + self.total_budget

        for attempt in range(1, self.max_attempts + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(
                    "SMTP budget of %.1fs exhausted before attempt %s (subject=%r)",
                    self.total_budget, attempt, subject,
                )
                break

            # Never let one attempt outlive the budget.
            try:
                self._deliver(to_email, msg, timeout=min(self.timeout, remaining))
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
                last_attempt = attempt == self.max_attempts
                logger.warning(
                    "SMTP send failed (attempt %s/%s, subject=%r)%s",
                    attempt, self.max_attempts, subject,
                    "" if last_attempt else " - retrying",
                    exc_info=True,
                )
                if last_attempt:
                    break
                # /** Stop on the BUDGET, not on the computed sleep. An earlier
                #     version broke out when `sleep_for <= 0`, which silently
                #     turned a legitimate `retry_delay=0` ("retry immediately")
                #     into "never retry" — one attempt and give up. The two
                #     conditions are different: having no delay to wait is not
                #     the same as having no time left. **/
                if deadline - time.monotonic() <= 0:
                    break
                # Sleep only as far as the budget allows, so the backoff can't
                # push the total past the deadline either.
                sleep_for = min(self.retry_delay * attempt, deadline - time.monotonic())
                if sleep_for > 0:
                    time.sleep(sleep_for)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Email service is temporarily unavailable.",
        )
