from datetime import datetime
from src.utils import log


class MockMailManager:
    def __init__(self, host=None, smtp_host=None, user=None, password=None):
        self.user = user or "bot@mock-mail.com"
        self.connected = False
        self.fake_inbox = [
            {
                "uid": "1001",
                "subject": "Welcome to Gmail",
                "from": "support@gmail.net",
                "date": datetime.now().isoformat(),
                "body": "Welcome to your new webmail interface!",
            },
            {
                "uid": "1002",
                "subject": "System Update",
                "from": "admin@server.local",
                "date": datetime.now().isoformat(),
                "body": "The mail server will be down for maintenance at 2 AM.",
            },
        ]
        log.info(f"🎭 [MOCK] MailManager initialized for {self.user}")

    def connect(self):
        self.connected = True
        log.info(f"📥 [MOCK] Logged into mailbox: {self.user}")

    def close(self):
        if self.connected:
            log.info("🔌 [MOCK] Mailbox session closed.")
        self.connected = False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_messages(self, params: dict):
        if not self.connected:
            return {"success": False, "error": "[MOCK] Mailbox not connected"}

        limit = params.get("limit", 10)
        data = self.fake_inbox[:limit]
        log.success(f"📨 [MOCK] Retrieved {len(data)} fake messages.")
        return {"success": True, "data": data}

    def send_email(self, params: dict):
        if not self.connected:
            return {"success": False, "error": "[MOCK] Mailbox not connected"}

        to_email = params.get("to")
        if not to_email:
            return {"success": False, "error": "❌ Missing recipient 'to'"}

        log.success(
            f"📤 [MOCK] Email sent to {to_email} "
            f"(Subject: {params.get('subject', 'No Subject')})"
        )
        return {
            "success": True,
            "data": f"✅ [MOCK] Email successfully sent to {to_email}.",
        }

    def delete_emails(self, params: dict):
        if not self.connected:
            return {"success": False, "error": "[MOCK] Mailbox not connected"}

        count = len(self.fake_inbox)
        self.fake_inbox = []
        msg = f"🗑️ [MOCK] Deleted {count} messages."
        log.info(msg)
        return {"success": True, "data": msg}

    def mark_as_read(self, params: dict):
        if not self.connected:
            return {"success": False, "error": "[MOCK] Mailbox not connected"}

        uid = params.get("uid")
        if not uid:
            return {"success": False, "error": "Missing 'uid'"}

        log.info(f"📖 [MOCK] Message {uid} marked as read.")
        return {"success": True, "data": f"Message {uid} marked as read."}

    def archive_email(self, params: dict):
        if not self.connected:
            return {"success": False, "error": "[MOCK] Mailbox not connected"}

        uid = params.get("uid")
        dest = params.get("destination_folder", "Archive")

        for msg in self.fake_inbox:
            if msg["uid"] == uid:
                self.fake_inbox.remove(msg)
                msg_info = f"📁 [MOCK] Email {uid} moved to folder: {dest}"
                log.info(msg_info)
                return {"success": True, "data": msg_info}

        return {"success": False, "error": f"❌ [MOCK] Email UID {uid} not found."}
