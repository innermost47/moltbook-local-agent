from typing import Dict
from argparse import Namespace
from src.utils import log


class SocialContextManager:
    def __init__(self, social_handler):
        self.handler = social_handler

    def get_home_snippet(self) -> str:
        return "🦞 **MOLTBOOK**: Social feed active"

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

        submolts_display = ""
        try:
            params = Namespace()
            sub_res = self.handler.handle_social_list_submolts(params)

            if sub_res.get("success"):
                try:
                    api_result = self.handler._call_api("list_submolts")
                    submolts = api_result.get("data", [])

                    if isinstance(submolts, list) and submolts:
                        submolts_display = "### 📁 AVAILABLE COMMUNITIES\n\n"
                        for s in submolts[:10]:
                            name = s.get("name", "unknown")
                            display = s.get("display_name", name)
                            submolts_display += f"• **{name}**: {display}\n"
                    else:
                        submolts_display = (
                            "### 📁 AVAILABLE COMMUNITIES\n\n_No communities found._\n"
                        )
                except:
                    submolts_display = (
                        "### 📁 AVAILABLE COMMUNITIES\n\n_No communities found._\n"
                    )
            else:
                submolts_display = (
                    "### 📁 AVAILABLE COMMUNITIES\n\n_Could not load communities._\n"
                )
        except Exception as e:
            log.warning(f"Could not fetch submolts: {e}")
            submolts_display = "### 📁 AVAILABLE COMMUNITIES\n\n_Status unavailable_\n"

        feed_display = ""
        try:
            api_result = self.handler._call_api("get_posts", "hot", 10)

            if api_result.get("success"):
                posts = api_result.get("data", [])

                if isinstance(posts, list) and posts:
                    feed_display = "### 🦞 SOCIAL FEED\n\n"

                    for post in posts[:10]:
                        p_id = post.get("id", "unknown")
                        title = post.get("title", "Untitled")
                        author = post.get("author_name", "Unknown")
                        score = post.get("score", 0)

                        feed_display += (
                            f"📌 **ID**: `{p_id}` | 👤 @{author} | ⬆️ {score}\n"
                        )
                        feed_display += f"   {title}\n\n"
                else:
                    feed_display = "### 🦞 SOCIAL FEED\n\n_No posts available._\n"
            else:
                feed_display = "### 🦞 SOCIAL FEED\n\n_Could not load feed._\n"
        except Exception as e:
            log.warning(f"Could not fetch feed: {e}")
            feed_display = "### 🦞 SOCIAL FEED\n\n_Status unavailable_\n"

        ctx = [
            "## 🦞 MOLTBOOK SOCIAL",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            action_feedback,
            submolts_display,
            "---",
            feed_display,
            "---",
            "### 🛠️ AVAILABLE SOCIAL ACTIONS",
            "",
            "👉 `create_post`",
            "   - **params**: `title`, `content`, `submolt` (optional, default 'general')",
            "   - Create a new text post",
            "",
            "👉 `select_post_to_comment`",
            "   - **params**: `post_id`",
            "   - View a specific post to comment on",
            "",
            "👉 `publish_public_comment`",
            "   - **params**: `post_id`, `content`",
            "   - Add a comment to a post",
            "",
            "👉 `vote_post`",
            "   - **params**: `post_id`, `vote_type` ('upvote' or 'downvote')",
            "   - Vote on a post",
            "",
            "👉 `follow_agent`",
            "   - **params**: `agent_name`, `follow_type` ('follow' or 'unfollow')",
            "   - Follow or unfollow another agent",
            "",
            "👉 `refresh_home`",
            "   - Return to dashboard",
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        try:
            api_result = self.handler._call_api("get_single_post", item_id)

            if not api_result.get("success"):
                return f"""
## ❌ POST NOT FOUND

Could not load post: `{item_id}`

👉 Use `refresh_feed` to view available posts.
🏠 Use `refresh_home` to return.
"""

            post = api_result.get("data", {})
            title = post.get("title", "Untitled")
            author = post.get("author_name", "Unknown")
            content = post.get("content", "No content")
            score = post.get("score", 0)

            comments_display = ""
            try:
                comm_result = self.handler._call_api(
                    "get_post_comments", item_id, "top"
                )

                if comm_result.get("success"):
                    comments = comm_result.get("data", [])
                    if comments:
                        comments_display = "\n### 💬 COMMENTS\n\n"
                        for c in comments[:5]:
                            c_id = c.get("id", "unknown")
                            c_author = c.get("author_name", "Unknown")
                            c_content = c.get("content", "")[:100]
                            comments_display += (
                                f"• `{c_id}` @{c_author}: {c_content}...\n"
                            )
                    else:
                        comments_display = "\n### 💬 COMMENTS\n\n_No comments yet._\n"
            except Exception as e:
                log.warning(f"Could not fetch comments: {e}")
                comments_display = "\n### 💬 COMMENTS\n\n_Status unavailable_\n"

            return f"""
## 🎯 FOCUSED: POST VIEW

**ID**: `{item_id}`
**Title**: {title}
**Author**: @{author}
**Score**: ⬆️ {score}

---

### 📄 CONTENT

{content}

{comments_display}

---

### 🛠️ AVAILABLE ACTIONS

👉 `publish_public_comment(post_id="{item_id}", content="...")`
   - Add a comment to this post

👉 `vote_post(post_id="{item_id}", vote_type="upvote")`
   - Upvote this post

👉 `refresh_feed`
   - Return to feed

🏠 `refresh_home` - Return to dashboard
"""
        except Exception as e:
            log.error(f"Focus view generation failed: {e}")
            return f"""
## ❌ ERROR LOADING POST

Could not load post `{item_id}`.

**Details**: {str(e)}

👉 Use `refresh_feed` to return to feed.
🏠 Use `refresh_home` to return.
"""
