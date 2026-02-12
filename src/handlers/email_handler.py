import smtplib
from email.message import EmailMessage
from typing import Dict, Any
from imap_tools import MailBox, MailMessageFlags
from bs4 import BeautifulSoup
from src.utils import log
from src.utils.exceptions import SystemLogicError


class EmailHandler:
    def __init__(self, host, smtp_host, user, password, test_mode=False):
        self.host = host
        self.smtp_host = smtp_host
        self.user = user
        self.password = password
        self.test_mode = test_mode
        self.mailbox = MailBox(self.host)
        self._authenticate()

    def _authenticate(self):
        try:
            self.mailbox.login(self.user, self.password, initial_folder="INBOX")
            log.info(f"📥 Mailbox connected: {self.user}")
        except Exception as e:
            log.error(f"❌ Email authentication failed: {e}")
            raise SystemLogicError(f"Could not connect to mail server: {e}")

    def handle_get_messages(self, params: Any) -> Dict:
        limit = getattr(params, "limit", 5)
        messages = []

        try:
            for msg in self.mailbox.fetch(limit=limit, reverse=True):
                body = msg.text or ""

                if not body.strip() and msg.html:
                    body = self._clean_html(msg.html)

                messages.append(
                    {
                        "uid": msg.uid,
                        "subject": msg.subject,
                        "from": msg.from_,
                        "date": msg.date.isoformat() if msg.date else None,
                        "body": body[:2000],
                    }
                )

            return {"success": True, "data": messages}
        except Exception as e:
            log.error(f"❌ Failed to fetch emails: {e}")
            return {"success": False, "error": str(e)}

    def _clean_html(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "lxml")
        for tag in ["script", "style", "head", "title", "meta"]:
            for element in soup(tag):
                element.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    def handle_send_email(self, params: Any) -> Dict:
        recipient = params.to
        subject = getattr(params, "subject", "Automated Update")
        content = params.content

        try:
            msg = EmailMessage()
            msg.set_content(content)
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = recipient

            with smtplib.SMTP(self.smtp_host, 587) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)

            log.success(f"📤 Email dispatched to {recipient}")
            return {"success": True, "data": f"Message sent to {recipient}."}
        except Exception as e:
            log.error(f"❌ SMTP Failure: {e}")
            return {"success": False, "error": f"Failed to send: {e}"}

    def handle_mark_as_read(self, params: Any) -> Dict:
        uid = params.uid
        try:
            self.mailbox.flag(uid, MailMessageFlags.SEEN, True)
            log.info(f"📖 Email {uid} marked as read.")
            return {"success": True, "data": f"Email {uid} marked as read."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_archive_email(self, params: Any) -> Dict:
        uid = params.uid
        folder = getattr(params, "destination", "Archive")
        try:
            self.mailbox.move(uid, folder)
            log.info(f"📁 Email {uid} moved to {folder}")
            return {"success": True, "data": f"Email {uid} moved to {folder}."}
        except Exception as e:
            return {"success": False, "error": f"Archiving failed: {e}"}

    def close(self):
        try:
            self.mailbox.logout()
            log.info("🔌 Email session terminated.")
        except:
            pass
