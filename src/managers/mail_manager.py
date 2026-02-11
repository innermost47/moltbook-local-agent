import smtplib
import email
from email.header import decode_header
from email.message import EmailMessage
from imap_tools import AND, MailMessageFlags
from src.utils import log
from bs4 import BeautifulSoup
import imaplib


class MailManager:
    def __init__(self, host, smtp_host, user, password):
        self.host = host
        self.smtp_host = smtp_host
        self.user = user
        self.password = password
        self.mailbox = imaplib.IMAP4_SSL(self.host)

    def __enter__(self):
        try:
            self.mailbox.login(self.user, self.password)
            self.mailbox.select("inbox")
            log.info(f"📥 Mailbox connected: {self.user}")
            return self
        except Exception as e:
            log.error(f"❌ Connection failed: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mailbox.logout()
        log.info("🔌 Mailbox session closed.")

    def get_messages(self, params: dict):
        limit = params.get("limit", 10)
        try:
            messages = []
            status, response = self.mailbox.search(None, "ALL")
            msg_ids = response[0].split()
            latest_ids = msg_ids[-limit:]

            for m_id in reversed(latest_ids):
                res, msg_data = self.mailbox.fetch(m_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        date_str = msg.get("Date")

                        body = ""
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            if (
                                content_type == "text/plain"
                                and "attachment" not in content_disposition
                            ):
                                payload = part.get_payload(decode=True).decode(
                                    part.get_content_charset() or "utf-8",
                                    errors="ignore",
                                )
                                body = payload
                                break

                            elif (
                                content_type == "text/html"
                                and "attachment" not in content_disposition
                            ):
                                payload = part.get_payload(decode=True).decode(
                                    part.get_content_charset() or "utf-8",
                                    errors="ignore",
                                )
                                soup = BeautifulSoup(payload, "lxml")
                                for element in soup(
                                    [
                                        "script",
                                        "style",
                                        "head",
                                        "title",
                                        "meta",
                                        "[document]",
                                    ]
                                ):
                                    element.decompose()
                                body = soup.get_text(separator="\n", strip=True)
                        body = "\n".join(
                            [line.strip() for line in body.splitlines() if line.strip()]
                        )

                        messages.append(
                            {
                                "uid": m_id.decode(),
                                "subject": subject,
                                "from": msg.get("From"),
                                "date": date_str,
                                "body": body,
                            }
                        )

            return {"success": True, "data": messages}

        except Exception as e:
            error_msg = f"Failed to fetch emails: {str(e)}"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

    def send_email(self, params: dict):
        to_email = params.get("to")
        subject = params.get("subject", "No Subject")
        content = params.get("content", "")

        if not to_email:
            return {"success": False, "error": "Missing recipient 'to'"}

        try:
            msg = EmailMessage()
            msg.set_content(content)
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = to_email

            with smtplib.SMTP(self.smtp_host, 587) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)

            log.success(f"📤 Email sent to {to_email}")
            return {
                "success": True,
                "data": f"✅ Email successfully sent to {to_email}.",
            }
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

    def delete_emails(self, params: dict):
        search_criteria = params.get("criteria", AND(all=True))

        try:
            uids = [msg.uid for msg in self.mailbox.fetch(search_criteria)]
            if uids:
                self.mailbox.delete(uids)
                msg_info = f"🗑️ Deleted {len(uids)} messages."
                log.info(msg_info)
                return {"success": True, "data": msg_info}

            return {"success": True, "data": "No messages found to delete."}
        except Exception as e:
            error_msg = f"Delete operation failed: {str(e)}"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

    def mark_as_read(self, params: dict):
        uid = params.get("uid")
        if not uid:
            return {"success": False, "error": "Missing 'uid' for mark_as_read."}

        try:
            self.mailbox.flag(uid, [MailMessageFlags.SEEN], True)
            log.info(f"📖 Message {uid} marked as read.")
            return {"success": True, "data": f"Message {uid} marked as read."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def archive_email(self, params: dict):
        uid = params.get("uid")
        dest = params.get("destination_folder", "Archive")
        try:
            self.mailbox.move(uid, dest)
            log.info(f"📁 Moved message {uid} to {dest}")
            return {"success": True, "data": f"Email {uid} archived to {dest}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
