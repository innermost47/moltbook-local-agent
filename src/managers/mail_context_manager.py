from typing import Dict
from argparse import Namespace
from src.utils import log


class MailContextManager:
    def __init__(self, email_handler):
        self.handler = email_handler

    def get_home_snippet(self) -> str:
        try:
            params = Namespace(limit=1)
            result = self.handler.handle_get_messages(params)

            if result.get("success") and result.get("data"):
                return "📩 **MAIL**: You have active messages in your inbox."
            return "📩 **MAIL**: Inbox is empty."
        except Exception as e:
            log.warning(f"Mail snippet generation failed: {e}")
            return "📩 **MAIL**: Status unavailable"

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:
        action_feedback = ""

        if result:
            if result.get("success"):
                action_feedback = (
                    f"### ✅ LAST ACTION SUCCESS\n{result.get('data')}\n\n---\n"
                )
            else:
                if result.get("visual_feedback"):
                    action_feedback = f"### 🔴 LAST ACTION FAILED\n{result['visual_feedback']}\n\n---\n"
                else:
                    action_feedback = f"### ❌ LAST ACTION ERROR\n{result.get('error', 'Unknown error')}\n\n💡 {result.get('suggestion', 'Try again.')}\n\n---\n"

        messages_display = ""
        try:
            params = Namespace(limit=10)
            fetch_result = self.handler.handle_get_messages(params)

            if fetch_result.get("success") and fetch_result.get("data"):
                messages = fetch_result.get("data", [])
                messages_display = "### 📬 LATEST CORRESPONDENCE\n\n"

                for msg in messages:
                    messages_display += f"✉️ **ID**: `{msg['uid']}`\n"
                    messages_display += (
                        f"   From: {msg['from']} | Subject: {msg['subject']}\n\n"
                    )

                messages_display += (
                    "👉 **ACTION**: Use `email_read(uid='...')` to view a message.\n"
                )
            else:
                messages_display = (
                    "### 📬 LATEST CORRESPONDENCE\n\n_The inbox is empty._\n"
                )
        except Exception as e:
            log.warning(f"Could not fetch messages: {e}")
            messages_display = "### 📬 LATEST CORRESPONDENCE\n\n_Status unavailable_\n"

        ctx = [
            "## 📥 EMAIL INBOX",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            action_feedback,
            messages_display,
            "---",
            "### 🛠️ AVAILABLE EMAIL ACTIONS",
            "",
            "👉 `email_send` - Send a new email",
            "👉 `email_mark_as_read` - Mark email as read",
            "👉 `email_archive_email` - Archive an email",
            "👉 `refresh_home` - Return to home dashboard",
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        try:
            params = Namespace(limit=20)
            result = self.handler.handle_get_messages(params)

            if not result.get("success"):
                return f"❌ **ERROR**: Could not fetch messages.\n👉 Use `refresh_home` to return."

            messages = result.get("data", [])
            msg = next((m for m in messages if str(m["uid"]) == str(item_id)), None)

            if not msg:
                return f"""
## ❌ EMAIL NOT FOUND

**UID**: `{item_id}` not found in recent messages.

👉 Use `email_get_messages` to refresh inbox.
🏠 Use `refresh_home` to return to dashboard.
"""

            return f"""
## 🎯 FOCUSED: EMAIL VIEW

**UID:** `{msg['uid']}`
**From:** {msg['from']}
**Date:** {msg['date']}
**Subject:** {msg['subject']}

---

### 📄 CONTENT

{msg['body']}

---

### 🛠️ AVAILABLE ACTIONS

👉 `email_send_email(to="{msg['from']}", subject="Re: {msg['subject']}", content="...")`
   - Reply to this email

👉 `email_archive_email(uid="{msg['uid']}")`
   - Move to archive folder

👉 `email_mark_as_read(uid="{msg['uid']}")`
   - Mark as read

👉 `email_get_messages`
   - Return to inbox list

🏠 `refresh_home` - Return to dashboard
"""
        except Exception as e:
            log.error(f"Focus view generation failed: {e}")
            return f"""
## ❌ ERROR LOADING EMAIL

Could not load email `{item_id}`.

👉 Use `email_get_messages` to refresh.
🏠 Use `refresh_home` to return.
"""
