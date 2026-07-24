import logging
import smtplib
from email.mime.text import MIMEText
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class Mailer:
    def __init__(
        self,
        server: str,
        port: int,
        username: str,
        password: str,
        sender_email: str,
        sender_name: str,
        timeout: float = 10.0,
    ):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.timeout = timeout

    def send_email(self, to_email: str, subject: str, body: str):
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.sender_email}>"
        msg["To"] = to_email

        try:
            # `timeout` prevents a slow/hung SMTP server from wedging the worker.
            with smtplib.SMTP(self.server, self.port, timeout=self.timeout) as smtp:
                smtp.starttls()
                smtp.login(self.username, self.password)
                smtp.sendmail(self.sender_email, [to_email], msg.as_string())
        except (smtplib.SMTPException, OSError, TimeoutError):
            logger.exception("SMTP send failed to %s (subject=%r)", to_email, subject)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Email service is temporarily unavailable.",
            )
