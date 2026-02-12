from typing import Dict
from src.managers.base_context_manager import BaseContextManager


class BlogContextManager(BaseContextManager):
    def __init__(self, blog_handler):
        self.handler = blog_handler

    def get_home_snippet(self) -> str:
        try:
            key_res = self.handler.handle_review_comment_key_requests(None)
            comm_res = self.handler.handle_review_pending_comments(
                type("Params", (), {"limit": 5})
            )

            key_count = 0
            if key_res.get("success") and "PENDING KEYS" in key_res.get("data", ""):
                key_count = max(0, len(key_res.get("data").splitlines()) - 1)

            comm_count = 0
            if comm_res.get("success") and "PENDING COMMENTS" in comm_res.get(
                "data", ""
            ):
                comm_count = max(0, len(comm_res.get("data").splitlines()) - 1)

            status_parts = ["📚 **BLOG**"]

            if key_count > 0:
                status_parts.append(f"🔑 **{key_count} Keys**")

            if comm_count > 0:
                status_parts.append(f"💬 **{comm_count} Comments**")

            if key_count == 0 and comm_count == 0:
                status_parts.append("All clear")

            return " | ".join(status_parts)

        except Exception:
            return "📚 **BLOG**: Connectivity check required."

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:
        action_feedback = ""
        if result and result.get("success"):
            action_feedback = (
                f"### ✅ LAST ACTION SUCCESS\n{result.get('data')}\n\n---\n"
            )

        blog_knowledge = ""
        try:
            articles_res = self.handler.blog_manager.list_articles()
            if articles_res and isinstance(articles_res, list):
                published_titles = [
                    post.get("title", "Untitled") for post in articles_res
                ][:10]

                blog_knowledge = "### 📚 PREVIOUSLY PUBLISHED ARTICLES\n"
                blog_knowledge += "- " + "\n- ".join(published_titles) + "\n"
                blog_knowledge += "\n**♟️ STRATEGIC INSTRUCTION**: Do not duplicate existing topics. Always provide a new angle.\n"
        except Exception as e:
            blog_knowledge = f"⚠️ _Note: Could not synchronize blog catalog ({e})_\n"

        key_context = ""
        try:
            pending_res = self.handler.handle_review_comment_key_requests(None)
            if pending_res.get("success") and "PENDING KEYS" in pending_res.get(
                "data", ""
            ):
                key_context = (
                    f"\n### 🔑 PENDING COMMENT KEY REQUESTS\n{pending_res['data']}\n"
                )
            else:
                key_context = "\n### 🔑 PENDING KEYS\n_No pending requests._\n"
        except Exception:
            key_context = ""

        ctx = [
            "## 📚 BLOG ADMINISTRATION & HUB",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            action_feedback,
            blog_knowledge,
            "---",
            key_context,
            "---",
            "### ✍️ MANDATORY BLOG ACTIONS",
            "You are already in BLOG mode. **Do not navigate.** Execute one of these:",
            "",
            "👉 `write_blog_article`",
            "   - **params**: `title` (string), `content` (markdown), `tags` (list of strings)",
            "   - *Note: Focus on your musical obsession.*",
            "",
            "👉 `review_pending_comments` or `handle_review_comment_key_requests`",
            "   - Use these to manage the resonance of your audience.",
            "",
            "👉 `refresh_home`",
            "   - Use this only if you wish to exit the Blog frequency.",
            "---",
            "⚠️ **WARNING**: Calling `Maps_to_mode('BLOG')` while already here creates a feedback loop of digital static. **Execute a write or review action now.**",
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        return f"""
# 🎯 FOCUS: BLOG KEY REQUEST
**Target ID:** {item_id}

You are currently reviewing the request for ID `{item_id}`. 
Review the list view or internal logs for the 'username' associated with this ID if necessary.

---
### 🛠️ DECISION
👉 **APPROVE**: `blog_approve_comment_key(request_id="{item_id}")`
👉 **REJECT**: `blog_reject_comment_key(request_id="{item_id}")`

💡 *Note: Approving will allow this user to comment on your articles.*

---
🏠 Use `blog_review_comment_key_requests` to go back to the list.
"""
