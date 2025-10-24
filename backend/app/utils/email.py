import smtplib
from email.mime.text import MIMEText

class Mailer:
    def __init__(
        self,
        server: str,
        port: int,
        username: str,
        password: str,
        sender_email: str,
        sender_name: str
    ):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.sender_name = sender_name

    def send_email(self, to_email: str, subject: str, body: str):
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.sender_email}>"
        msg["To"] = to_email

        with smtplib.SMTP(self.server, self.port) as smtp:
            smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.sendmail(self.sender_email, [to_email], msg.as_string())
