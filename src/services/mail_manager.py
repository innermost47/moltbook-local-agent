import smtplib
from email.message import EmailMessage
from imap_tools import MailBox, AND, MailMessageFlags
from src.utils import log


class MailManager:
    def __init__(self, host, smtp_host, user, password):
        self.host = host
        self.smtp_host = smtp_host
        self.user = user
        self.password = password
        self.mailbox = MailBox(self.host)

    def __enter__(self):
        try:
            self.mailbox.login(self.user, self.password)
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
            for msg in self.mailbox.fetch(limit=limit, reverse=True):
                messages.append(
                    {
                        "uid": msg.uid,
                        "subject": msg.subject,
                        "from": msg.from_,
                        "date": msg.date.isoformat() if msg.date else None,
                        "body": msg.text or msg.html,
                    }
                )

            log.success(f"📨 Retrieved {len(messages)} messages.")
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

            with smtplib.SMTP_SSL(self.smtp_host, 465) as server:
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
