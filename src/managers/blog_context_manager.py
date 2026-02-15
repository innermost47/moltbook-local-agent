from typing import Dict
from argparse import Namespace
from src.managers.base_context_manager import BaseContextManager
from src.utils import log


class BlogContextManager(BaseContextManager):
    def __init__(self, blog_handler):
        self.handler = blog_handler

    def get_home_snippet(self) -> str:
        try:
            key_params = Namespace()
            comm_params = Namespace(limit=5)

            key_res = self.handler.handle_review_comment_key_requests(key_params)
            comm_res = self.handler.handle_review_pending_comments(comm_params)

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
                status_parts.append(f"🔑 {key_count} Keys")

            if comm_count > 0:
                status_parts.append(f"💬 {comm_count} Comments")

            if key_count == 0 and comm_count == 0:
                status_parts.append("All clear")

            return " | ".join(status_parts)

        except Exception as e:
            log.warning(f"Blog snippet generation failed: {e}")
            return "📚 **BLOG**: Status unavailable"

    def get_list_view(
        self, status_msg: str = "", result: Dict = None, workspace_pins=None
    ) -> str:

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
            log.warning(f"Could not sync blog catalog: {e}")
            blog_knowledge = f"⚠️ _Note: Could not synchronize blog catalog_\n"

        key_context = ""
        try:
            key_params = Namespace()
            pending_res = self.handler.handle_review_comment_key_requests(key_params)

            if pending_res.get("success") and "PENDING KEYS" in pending_res.get(
                "data", ""
            ):
                key_context = (
                    f"\n### 🔑 PENDING COMMENT KEY REQUESTS\n{pending_res['data']}\n"
                )
            else:
                key_context = "\n### 🔑 PENDING KEYS\n_No pending requests._\n"
        except Exception as e:
            log.warning(f"Could not fetch key requests: {e}")
            key_context = "\n### 🔑 PENDING KEYS\n_Status unavailable_\n"

        ctx = [
            "## 📚 BLOG ADMINISTRATION & HUB",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            blog_knowledge,
            "---",
            key_context,
            "---",
            "### ✍️ AVAILABLE BLOG ACTIONS",
            "You are in BLOG mode. **Do not navigate.** Execute one of these:",
            "",
            "👉 `write_blog_article`",
            "   - **params**: `title`, `excerpt`, `content` (markdown), `image_prompt`",
            "   - Create a new blog post with AI-generated header image",
            "   - ⚠️ CRITICAL: Write content DIRECTLY as the article, NOT 'I will write about...'",
            "   - 💡 **After publishing**: Use `pin_to_workspace` to save the article URL, then navigate to SOCIAL to share it with `share_link`",
            "",
            "👉 `review_pending_comments`",
            "   - Review and moderate pending blog comments",
            "",
            "👉 `review_comment_key_requests`",
            "   - Review access requests for commenting privileges",
            "",
            "⚠️ **WARNING**: Do not call `navigate_to_mode('BLOG')` while already here. Execute an action instead.",
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:

        return f"""
## 🎯 FOCUS: BLOG KEY REQUEST

**Target ID:** `{item_id}`

You are reviewing the comment key request for ID `{item_id}`. 
Review the list view for the 'username' associated with this ID if needed.

---

### 🛠️ DECISION ACTIONS

👉 **APPROVE**: `approve_comment_key(request_id="{item_id}")`
   - Grant this user permission to comment on your articles

👉 **REJECT**: `reject_comment_key(request_id="{item_id}")`
   - Deny commenting access to this user

---

💡 **TIP**: Use `review_comment_key_requests` to return to the full list.
"""
