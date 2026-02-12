from typing import Dict


class MailContextManager:
    def __init__(self, email_handler):
        self.handler = email_handler

    def get_home_snippet(self) -> str:
        try:
            result = self.handler.handle_get_messages(type("Params", (), {"limit": 1}))
            if result.get("success") and result.get("data"):
                return f"📩 **MAIL**: You have active messages in your inbox."
            return "📩 **MAIL**: Inbox is empty."
        except Exception:
            return "📩 **MAIL**: Connection status unknown."

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:
        dynamic_feedback = ""
        if result and result.get("success"):
            if "results" in result:
                dynamic_feedback = "### 🔍 FILTERED RESULTS\n"
                for res in result.get("results", []):
                    dynamic_feedback += f"• {res}\n"
                dynamic_feedback += "\n---\n"

        fetch_result = self.handler.handle_get_messages(
            type("Params", (), {"limit": 10})
        )

        ctx = [
            "## 📥 EMAIL INBOX",
            f"{status_msg}" if status_msg else "",
            "---",
            dynamic_feedback,
            "### 📬 LATEST CORRESPONDENCE",
        ]

        if fetch_result.get("success") and fetch_result.get("data"):
            messages = fetch_result.get("data", [])
            for msg in messages:
                ctx.append(f"✉️ **ID**: `{msg['uid']}`")
                ctx.append(f"   From: {msg['from']} | Sub: {msg['subject']}")
                ctx.append("")
            ctx.append(
                "👉 **ACTION**: Use `email_read(uid='...')` to focus on a frequency."
            )
        else:
            ctx.append("_The silence of the inbox is absolute._")

        ctx.append("\n---")
        ctx.append("👉 **QUICK**: `email_send` | `email_mark_read` | `refresh_home`")

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        result = self.handler.handle_get_messages(type("Params", (), {"limit": 20}))
        messages = result.get("data", [])
        msg = next((m for m in messages if str(m["uid"]) == str(item_id)), None)

        if not msg:
            return f"❌ **ERROR**: Email `{item_id}` not found in the latest fetch.\n👉 Use `email_get_messages` to refresh."

        return f"""
# 🎯 FOCUSED: EMAIL VIEW
**UID:** {msg['uid']}
**From:** {msg['from']}
**Date:** {msg['date']}
**Subject:** {msg['subject']}

**CONTENT:**
{msg['body']}

---
### 🛠️ AVAILABLE ACTIONS
👉 **REPLY**: `email_send_email(to="{msg['from']}", subject="Re: {msg['subject']}", content="...")`
👉 **ARCHIVE**: `email_archive_email(uid="{msg['uid']}")`
👉 **MARK READ**: `email_mark_as_read(uid="{msg['uid']}")`

🏠 Use `email_get_messages` to go back to inbox.
"""
