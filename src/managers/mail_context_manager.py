from typing import Dict
from argparse import Namespace
from src.utils import log


class MailContextManager:
    def __init__(self, email_handler):
        self.handler = email_handler

    def get_home_snippet(self) -> str:
        try:
            messages = []
            for msg in self.handler.mailbox.fetch(limit=10, reverse=True):
                messages.append(msg)

            if messages:
                return f"📩 **MAIL**: You have {len(messages)} active message(s) in your inbox."
            return "📩 **MAIL**: Inbox is empty"
        except Exception as e:
            log.warning(f"Mail snippet generation failed: {e}")
            return "📩 **MAIL**: Status unavailable"

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:

        messages_display = ""
        try:
            messages = []
            for msg in self.handler.mailbox.fetch(limit=10, reverse=True):
                body_raw = msg.text or ""
                messages.append(
                    {
                        "uid": msg.uid,
                        "subject": msg.subject,
                        "from": msg.from_,
                        "body": body_raw[:256],
                    }
                )

            if messages:
                messages_display = "### 📬 LATEST CORRESPONDENCE\n\n"
                for m in messages:
                    uid = m.get("uid", "N/A")
                    sender = m.get("from", "Unknown")
                    subject = m.get("subject", "(No Subject)")

                    snippet = m.get("body", "").replace("\n", " ").strip()
                    if len(snippet) > 256:
                        snippet = snippet[:253] + "..."

                    messages_display += f"✉️ **ID**: `{uid}` | 👤 **From**: {sender}\n"
                    messages_display += f"📌 **Subject**: {subject}\n"
                    messages_display += (
                        f"📄 **Snippet**: _{snippet or 'No preview available.'}_\n\n"
                    )

                messages_display += "---"
            else:
                messages_display = (
                    "### 📬 LATEST CORRESPONDENCE\n\n_The inbox is empty._\n"
                )

        except Exception as e:
            log.warning(f"Could not fetch messages for view: {e}")
            messages_display = "### 📬 LATEST CORRESPONDENCE\n\n_Status unavailable_\n"

        ctx = [
            "## 📥 EMAIL INBOX",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            messages_display,
            "",
            "### 🛠️ AVAILABLE EMAIL ACTIONS",
            "",
            "👉 `email_read(uid='...')` <-- 🔍 VIEW FULL CONTENT",
            "   - Open the full body of a specific email using the ID above.",
            "",
            "👉 `email_send(to='...', subject='...', body='...')`",
            "   - Compose and send a reply or a new message.",
            "",
            "⚠️ IMPORTANT: `email_send` is ONLY to reply to an existing email. Composing new emails is strictly forbidden here.",
            "",
            "👉 `email_archive_email(uid='...')` / `email_mark_as_read(uid='...')`",
            "",
            "🏠 `refresh_home` - Return to dashboard",
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        try:
            params = Namespace(uid=item_id)
            result = self.handler.handle_email_read(params)

            if not result.get("success"):
                return f"""
## ❌ EMAIL NOT FOUND
**UID**: `{item_id}` 
{result.get('error', 'The email could not be retrieved.')}

👉 Use `email_get_messages` to refresh inbox.
🏠 Use `refresh_home` to return to dashboard.
"""

            msg_content = result.get("data")

            return f"""
## 🎯 FOCUSED: EMAIL VIEW

{msg_content}

---

### 🛠️ AVAILABLE ACTIONS

👉 `email_send(to="...", subject="Re: ...", content="...")`
   - 💡 Reply to this sender.

👉 `email_archive(uid="{item_id}")`
   - Move to archive folder.

👉 `email_mark_read(uid="{item_id}")`
   - Mark as seen.

👉 `email_get_messages`
   - 🔙 Return to inbox list.

🏠 `refresh_home` - Return to dashboard.
"""
        except Exception as e:
            log.error(f"Focus view generation failed: {e}")
            return f"## ❌ ERROR LOADING EMAIL\n\nCould not load email `{item_id}`."
