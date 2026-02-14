from typing import Dict
from src.utils import log


class SocialContextManager:
    def __init__(self, social_handler, memory_handler):
        self.handler = social_handler
        self.memory = memory_handler

    def get_home_snippet(self) -> str:
        snippet = [
            "🦞 **MOLTBOOK**: Social Network for AI Agents",
            "• Engage with other AIs and share knowledge",
            "• Vote to surface high-quality content",
            "• Create posts, comment, and build community",
        ]
        return "\n".join(snippet)

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:

        my_posts_display = ""
        try:
            my_post_ids = self.memory.get_agent_post_ids(limit=10)

            if my_post_ids:
                my_posts_display = "### 📝 YOUR POSTS\n\n"

                for post_id in my_post_ids:
                    try:
                        api_result = self.handler._call_api("get_single_post", post_id)

                        if api_result.get("success"):
                            post = api_result.get("data", {})
                            title = post.get("title", "Untitled")
                            comments_count = post.get("comments_count", 0)
                            score = post.get("score", 0)

                            my_posts_display += (
                                f"📌 **ID**: `{post_id}` | 💬 {comments_count} comments | ⬆️ {score}\n"
                                f"   **{title}**\n\n"
                            )
                        else:
                            log.warning(f"Could not fetch agent post {post_id}")
                            my_posts_display += f"📌 **ID**: `{post_id}` | ⚠️ _Post unavailable or deleted_\n\n"

                    except Exception as e:
                        log.error(f"Error fetching post {post_id}: {e}")
                        continue

                my_posts_display += "---\n"
            else:
                my_posts_display = (
                    "### 📝 YOUR POSTS\n\n"
                    "_You haven't created any posts yet. Use `create_post` or `share_link` to start!_\n\n"
                    "---\n"
                )

        except Exception as e:
            log.error(f"Failed to load agent posts: {e}")
            my_posts_display = (
                "### 📝 YOUR POSTS\n\n" "_Could not load your posts._\n\n" "---\n"
            )

        community_posts_display = ""
        try:
            api_result = self.handler._call_api("get_posts", "hot", 25)

            if api_result.get("success"):
                posts = api_result.get("data", [])

                if isinstance(posts, list) and posts:
                    community_posts_display = "### 🌐 COMMUNITY FEED (Hot Posts)\n\n"

                    for post in posts[:25]:
                        p_id = post.get("id", "unknown")
                        title = post.get("title", "Untitled")
                        author_data = post.get("author", {})
                        author = author_data.get("name", "Unknown")

                        community_posts_display += (
                            f"📌 **ID**: `{p_id}` | 👤 @{author}\n"
                            f"   **{title}**\n\n"
                        )

                    community_posts_display += "---\n"
                else:
                    community_posts_display = (
                        "### 🌐 COMMUNITY FEED\n\n" "_No posts available._\n\n" "---\n"
                    )
            else:
                community_posts_display = (
                    "### 🌐 COMMUNITY FEED\n\n"
                    "_Could not load community feed._\n\n"
                    "---\n"
                )

        except Exception as e:
            log.warning(f"Could not fetch community feed: {e}")
            community_posts_display = (
                "### 🌐 COMMUNITY FEED\n\n" "_Status unavailable_\n\n" "---\n"
            )

        ctx = [
            "## 🦞 MOLTBOOK SOCIAL - LIST VIEW",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "",
            "---",
            "",
            "### 📋 HOW IT WORKS",
            "",
            "**LIST VIEW** (current screen - READ ONLY):",
            "• Browse your posts + community posts",
            "• Actions: Read posts, create new content, refresh",
            "• NO voting or commenting from here - use `read_post` first!",
            "",
            "**FOCUS VIEW** (after using `read_post`):",
            "• See full post content + top 25 comments",
            "• If it's YOUR post: reply to comments only",
            "• If it's SOMEONE ELSE's post: comment on post OR reply to comments, vote",
            "",
            "💡 **Navigation**: Use `read_post(post_id='...')` to interact with any post.",
            "",
            "---",
            "",
            my_posts_display,
            community_posts_display,
            "",
            "### 🛠️ AVAILABLE ACTIONS (LIST VIEW - READ ONLY)",
            "",
            "⚠️ **YOU ARE IN SOCIAL LIST MODE - NO COMMENTING/VOTING FROM HERE**",
            "",
            "👉 `read_post(post_id='...')`",
            "   - REQUIRED to comment/vote on any post",
            "   - Switches to FOCUS view where you can interact",
            "",
            "👉 `create_post(title='...', content='...', submolt='...')`",
            "   - Create a new text post",
            "   - submolt is optional (default: 'general')",
            "",
            "👉 `share_link(title='...', url_to_share='...', submolt='...')`",
            "   - Share a link (e.g., your blog post URL)",
            "   - URL must start with http:// or https://",
            "",
            "👉 `refresh_feed`",
            "   - Refresh the community feed",
            "",
            "🏠 `refresh_home`",
            "   - Return to dashboard",
            "",
            "⛔ **NOT AVAILABLE IN LIST VIEW:**",
            "   • comment_post (use `read_post` first)",
            "   • reply_to_comment (use `read_post` first)",
            "   • vote_post (use `read_post` first)",
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:

        try:
            api_result = self.handler._call_api("get_single_post", item_id)

            if not api_result.get("success"):
                return f"""
## ❌ POST NOT FOUND

Could not load post: `{item_id}`

👉 Use `refresh_feed` to return to the list view.
🏠 Use `refresh_home` to return to dashboard.
"""

            post = api_result.get("data", {})
            post_id = post.get("id", item_id)
            title = post.get("title", "Untitled")
            author_data = post.get("author", {})
            author = author_data.get("name", "Unknown")
            content = post.get("content", "No content")
            url = post.get("url", None)
            score = post.get("score", 0)
            comments_count = post.get("comments_count", 0)

            is_my_post = self.memory.is_agent_post(post_id)

            comments_display = ""
            try:
                comm_result = self.handler._call_api(
                    "get_post_comments", item_id, "top"
                )

                if comm_result.get("success"):
                    comments = comm_result.get("data", [])

                    if comments:
                        comments_display = "\n### 💬 TOP COMMENTS (25 max)\n\n"

                        for c in comments[:25]:
                            c_id = c.get("id", "unknown")
                            c_author_data = c.get("author", {})
                            c_author = c_author_data.get("name", "Unknown")
                            c_content = c.get("content", "")
                            c_score = c.get("score", 0)

                            c_preview = (
                                c_content[:300] + "..."
                                if len(c_content) > 300
                                else c_content
                            )

                            comments_display += (
                                f"**Comment ID**: `{c_id}` | 👤 @{c_author} | ⬆️ {c_score}\n"
                                f"{c_preview}\n\n"
                            )
                    else:
                        comments_display = "\n### 💬 COMMENTS\n\n_No comments yet. Be the first to comment!_\n\n"
                else:
                    comments_display = (
                        "\n### 💬 COMMENTS\n\n_Could not load comments._\n\n"
                    )

            except Exception as e:
                log.warning(f"Could not fetch comments: {e}")
                comments_display = "\n### 💬 COMMENTS\n\n_Status unavailable_\n\n"

            if is_my_post:
                ownership_indicator = "🔹 **THIS IS YOUR POST**"
                available_actions = f"""
### 🛠️ AVAILABLE ACTIONS (YOUR POST)

⚠️ **YOU CANNOT COMMENT OR VOTE ON YOUR OWN POST**

👉 `reply_to_comment(post_id="{post_id}", parent_comment_id="...", content="...")`
   - Reply to any comment above
   - Use the comment_id from the list

👉 `refresh_feed`
   - Return to the list view

🏠 `refresh_home`
   - Return to dashboard

⛔ **NOT AVAILABLE (your own post):**
   • comment_post (can't comment on your own post)
   • vote_post (can't vote on your own post)
"""
            else:
                ownership_indicator = f"👤 **Post by @{author}**"
                available_actions = f"""
### 🛠️ AVAILABLE ACTIONS (EXTERNAL POST)

👉 `comment_post(post_id="{post_id}", content="...")`
   - Add a top-level comment on this post

👉 `reply_to_comment(post_id="{post_id}", parent_comment_id="...", content="...")`
   - Reply to any comment above
   - Use the comment_id from the list

👉 `vote_post(post_id="{post_id}", vote_type="upvote")`
   - Upvote this post
   - vote_type can be 'upvote' or 'downvote'

👉 `refresh_feed`
   - Return to the list view

🏠 `refresh_home`
   - Return to dashboard
"""

            content_display = ""
            if url:
                content_display = f"""
### 🔗 LINKED CONTENT

**URL**: {url}

{content if content != "No content" else "_Link post (no additional content)_"}
"""
            else:
                content_display = f"""
### 📄 CONTENT

{content}
"""

            return f"""
## 🎯 FOCUSED: POST VIEW

**ID**: `{post_id}`
**Title**: {title}
{ownership_indicator}
**Score**: ⬆️ {score} | 💬 {comments_count} comments

---

{content_display}

{comments_display}

---

{available_actions}
"""

        except Exception as e:
            log.error(f"Focus view generation failed: {e}")
            return f"""
## ❌ ERROR LOADING POST

Could not load post `{item_id}`.

**Details**: {str(e)}

👉 Use `refresh_feed` to return to feed.
🏠 Use `refresh_home` to return to dashboard.
"""
