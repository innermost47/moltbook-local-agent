import random
from typing import Dict


class SocialContextManager:
    def __init__(self, social_handler):
        self.handler = social_handler
        self.feed_options = ["hot", "new", "top", "rising"]

    def _get_enriched_feed_context(self, posts_data: Dict) -> str:
        enriched_lines = []
        posts = posts_data.get("posts", [])

        for post in posts[:15]:
            p_id = post["id"]
            enriched_lines.append(
                f"📌 **POST ID**: `{p_id}` | 👤 @{post['author_name']}"
            )
            enriched_lines.append(f"   Title: {post['title']}")

            CommParams = type("Params", (), {"post_id": p_id, "sort": "top"})
            comm_res = self.handler.handle_social_get_comments(CommParams())

            if comm_res.get("success") and comm_res.get("comments"):
                comments = comm_res.get("comments", [])
                enriched_lines.append("   💬 Recent Comments:")
                for c in comments[:3]:
                    enriched_lines.append(
                        f"     - [`{c['id']}`] @{c['author_name']}: {c['content'][:100]}..."
                    )
            else:
                enriched_lines.append("   💬 _No comments yet._")

            enriched_lines.append("")

        return "\n".join(enriched_lines)

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:
        interaction_feedback = ""
        if result and result.get("success"):
            if result.get("action_type") in [
                "social_comment",
                "social_vote",
                "social_create_post",
            ]:
                interaction_feedback = (
                    f"### ✅ ACTION RESULT\n{result.get('data')}\n\n---\n"
                )

        sort = random.choice(self.feed_options)
        Params = type("Params", (), {"sort": sort, "limit": 20})
        posts_data = self.handler.handle_social_get_feed(Params())

        if not posts_data.get("success") or not posts_data.get("posts"):
            return "❌ **ERROR**: Failed to retrieve social feed. Service unavailable."

        sub_res = self.handler.handle_social_list_submolts(None)
        submolts = sub_res.get("submolts", []) if sub_res.get("success") else []
        submolts_formatted = "\n".join(
            [f"- {s['name']}: {s.get('description', '')}" for s in submolts]
        )

        enriched_feed = self._get_enriched_feed_context(posts_data)

        ctx = [
            "## 📁 AVAILABLE COMMUNITIES (SUBMOLTS)",
            submolts_formatted if submolts_formatted else "- No communities found.",
            "",
            "### 💡 USAGE NOTES:",
            "- Post in relevant communities to ensure maximum visibility and engagement.",
            "---",
            "## 🦞 SOCIAL FEED (ENRICHED)",
            f"{status_msg}" if status_msg else "",
            interaction_feedback,
            enriched_feed,
            "**⚠️ WARNING: Use the exact IDs provided. Do not modify or truncate them.**",
            "---",
            "👉 **ACTIONS**: `social_comment` | `social_vote` | `social_create_post`",
            "👉 **NAVIGATION**: `refresh_home` to exit.",
        ]

        return "\n".join(ctx)

    def get_home_snippet(self) -> str:
        return "🦞 **MOLTBOOK**: Feed enriched with latest posts and comments."

    def get_focus_view(self, item_id: str) -> str:
        return f"Focusing on thread {item_id}... (Full content view)"
