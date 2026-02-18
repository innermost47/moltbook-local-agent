from typing import Dict
from argparse import Namespace
from src.utils import log
from src.contexts.base_context import BaseContext


class MailContext(BaseContext):
    def __init__(self, email_handler, memory_handler):
        self.handler = email_handler
        self.memory = memory_handler

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

    def get_list_view(
        self, status_msg: str = "", result: Dict = None, workspace_pins=None
    ) -> str:
        owned_tools = set(self.memory.get_owned_tools())
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

        available_actions = []
        locked_actions = []

        available_actions.append(
            """
👉 Current view shows your inbox (free access)
   - You can see message list without purchasing tools
"""
        )

        if "email_read" in owned_tools:
            available_actions.append(
                """
👉 `email_read(uid='...')`
   - Open and read full email content
"""
            )
        else:
            locked_actions.append("🔒 `email_read` - 100 XP (unlock to read emails)")

        if "email_send" in owned_tools:
            available_actions.append(
                """
👉 `email_send(to='...', subject='...', body='...')`
   - Send or reply to emails
   - ⚠️ Use ONLY to reply to existing emails
"""
            )
        else:
            locked_actions.append("🔒 `email_send` - 100 XP (unlock to send)")

        if "email_delete" in owned_tools:
            available_actions.append(
                """
👉 `email_delete(uid='...')`
   - Delete or archive messages
"""
            )
        else:
            locked_actions.append("🔒 `email_delete` - 100 XP (unlock to manage)")

        actions_section = "### 🛠️ AVAILABLE EMAIL ACTIONS\n\n"

        if len(available_actions) > 1:
            actions_section += "You are in EMAIL mode. Execute one of these:\n\n"
            actions_section += "\n".join(available_actions)
        else:
            actions_section += "⚠️ **LIMITED ACCESS**\n\n"
            actions_section += (
                "You can VIEW the inbox (free), but can't interact yet.\n\n"
            )
            actions_section += available_actions[0]

        if locked_actions:
            actions_section += "\n\n### 🔒 LOCKED ACTIONS\n"
            actions_section += "Purchase these tools to unlock email management:\n\n"
            actions_section += "\n".join(locked_actions)
            actions_section += "\n\n💡 Navigate to HOME and use `visit_shop` to unlock."

        all_email_owned = {"email_read", "email_send", "email_delete"}.issubset(
            owned_tools
        )
        if all_email_owned:
            actions_section = (
                "### 🛠️ AVAILABLE EMAIL ACTIONS\n\n✅ **Full email access unlocked!**\n\n"
                + "\n".join(available_actions)
            )

        ctx = [
            "## 📥 EMAIL INBOX",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            messages_display,
            "",
            actions_section,
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
"""
        except Exception as e:
            log.error(f"Focus view generation failed: {e}")
            return f"## ❌ ERROR LOADING EMAIL\n\nCould not load email `{item_id}`."
