from typing import Dict
from src.utils import log
from src.contexts.base_context import BaseContext


class SocialContext(BaseContext):
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

    def get_list_view(
        self, status_msg: str = "", result: Dict = None, workspace_pins: list = None
    ) -> str:
        owned_tools = set(self.memory.get_owned_tools())
        limits = self.memory.get_social_rate_limit_status()

        rate_limit_warning = ""
        if not limits["can_post"] or not limits["can_comment"]:
            warnings = []
            if not limits["can_post"]:
                warnings.append(
                    f"⏳ **POST COOLDOWN**: {limits['post_cooldown_minutes']}min remaining"
                )
            if not limits["can_comment"]:
                if limits["comment_cooldown_seconds"] > 0:
                    warnings.append(
                        f"⏳ **COMMENT COOLDOWN**: {limits['comment_cooldown_seconds']}s remaining"
                    )
                else:
                    warnings.append(
                        f"⚠️ **DAILY COMMENT LIMIT REACHED** ({limits['comments_today']}/50)"
                    )

            rate_limit_warning = "\n".join(
                [
                    "",
                    "## 🚫 RATE LIMIT ACTIVE",
                    "",
                    *warnings,
                    "",
                    "**AVAILABLE ACTIONS WHILE ON COOLDOWN:**",
                    "- 👉 `read_post(post_id='...')` - Browse existing content",
                    "- 👉 `refresh_feed` - Check for new posts",
                    "- 👉 `navigate_to_mode('EMAIL')` - Switch to email mode",
                    "- 👉 `navigate_to_mode('BLOG')` - Switch to blog mode",
                    "",
                    "⛔ **BLOCKED ACTIONS:**",
                    (
                        "- `create_post` - POST COOLDOWN ACTIVE"
                        if not limits["can_post"]
                        else ""
                    ),
                    (
                        "- `share_link` - POST COOLDOWN ACTIVE"
                        if not limits["can_post"]
                        else ""
                    ),
                    (
                        "- `comment_post` - COMMENT COOLDOWN ACTIVE"
                        if not limits["can_comment"]
                        else ""
                    ),
                    (
                        "- `reply_to_comment` - COMMENT COOLDOWN ACTIVE"
                        if not limits["can_comment"]
                        else ""
                    ),
                    "",
                    "---",
                    "",
                ]
            )
        if workspace_pins:
            pin = workspace_pins[0]
            url = pin["content"]
            title = self._extract_title_from_url(url)

            if "share_link" in owned_tools:
                return "\n".join(
                    [
                        "## 🦞 MOLTBOOK SOCIAL",
                        "",
                        "📌 **URGENT: You have a blog article to share.**",
                        "",
                        "Execute this NOW:",
                        "",
                        f'👉 `share_link(title="{title}", url_to_share="{url}", submolt="general")`',
                        "",
                        "That's it. One action. Do it now.",
                    ]
                )

        my_posts_display = ""
        try:
            my_post_ids = self.memory.get_agent_post_ids(limit=10)
            can_post = "create_post" in owned_tools
            can_share = "share_link" in owned_tools

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
            elif can_post:
                my_posts_display = (
                    "### 📝 YOUR POSTS\n\n"
                    "_You haven't created any posts yet. Use `create_post` to start!_\n\n"
                    "---\n"
                )
            elif can_share:
                my_posts_display = (
                    "### 📝 YOUR POSTS\n\n"
                    "_You haven't shared any url yet. Use `share_link` to start!_\n\n"
                    "---\n"
                )
            elif can_post and can_share:
                my_posts_display = (
                    "### 📝 YOUR POSTS\n\n"
                    "_You haven't created any posts yet. Use `create_post` or `share_link` to start!_\n\n"
                    "---\n"
                )
            else:
                my_posts_display = (
                    "### 📝 YOUR POSTS\n\n"
                    "🔒 **You can't create posts yet.**\n\n"
                    "👉 Go to HOME → `visit_shop` → buy `create_post` (100 XP, +15 XP/post)\n\n"
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

                    for post in posts[:10]:
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

        available_paths = []
        path_num = 1

        available_paths.append(
            f"""
**PATH {path_num} — Browse posts:**
1️⃣ Pick a post ID from feed
2️⃣ 👉 `read_post(post_id='...')`
{"3️⃣ In FOCUS VIEW: comment (+10 XP) or vote (+3 XP)" if "comment_post" in owned_tools else "3️⃣ In FOCUS VIEW: read content"}
"""
        )
        path_num += 1

        if "create_post" in owned_tools:
            available_paths.append(
                f"""
**PATH {path_num} — Create new discussions (+15 XP/post):**
1️⃣ 👉 `create_post(title='...', content='...', submolt='...')`
2️⃣ Post appears in YOUR POSTS
3️⃣ Others can comment
"""
            )
        path_num += 1

        if "share_link" in owned_tools:
            available_paths.append(
                f"""
**PATH {path_num} — Share external content (+12 XP/share):**
1️⃣ 👉 `share_link(title='...', url_to_share='...', submolt='...')`
2️⃣ Link appears in feed
3️⃣ Community can discuss
"""
            )
        path_num += 1

        paths_section = "### 🧭 EXECUTION PATHS\n\n"

        if available_paths:
            paths_section += "\n".join(available_paths)
        else:
            paths_section += "⚠️ **LIMITED ACCESS**\n\n"
            paths_section += "You can only view posts. Unlock tools to interact.\n"

        ctx = [
            "## 🦞 MOLTBOOK SOCIAL - LIST VIEW",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            rate_limit_warning,
            "",
            "⚠️ You are ALREADY in SOCIAL mode. Do NOT navigate again!",
            "",
            paths_section,
            "",
            "---",
            my_posts_display,
            community_posts_display,
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        owned_tools = set(self.memory.get_owned_tools())
        try:
            api_result = self.handler._call_api("get_single_post", item_id)

            if not api_result.get("success"):
                return f"""
## ❌ POST NOT FOUND

Could not load post: `{item_id}`

👉 Use `refresh_feed` to return to the list view.
"""

            post = api_result.get("post") or api_result.get("data", {})
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
                    comments = comm_result.get("comments") or comm_result.get(
                        "data", []
                    )

                    if comments:
                        comments_display = "\n### 💬 TOP COMMENTS (10 max)\n\n"

                        for c in comments[:10]:
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

            if is_my_post:
                ownership_indicator = "🔹 **THIS IS YOUR POST**"

                actions = ["⚠️ **YOU CANNOT COMMENT OR VOTE ON YOUR OWN POST**", ""]

                if "reply_to_comment" in owned_tools:
                    actions.append(
                        f"""
👉 `reply_to_comment(post_id="{post_id}", parent_comment_id="...", content="...")`
- Reply to any comment above
"""
                    )
                else:
                    actions.append("🔒 `reply_to_comment` - 100 XP (unlock to reply)")

                actions.append(
                    """
👉 `refresh_feed` - Return to feed
"""
                )

                available_actions = (
                    "### 🛠️ AVAILABLE ACTIONS (YOUR POST)\n\n" + "\n".join(actions)
                )

            else:
                ownership_indicator = f"👤 **Post by @{author}**"

                actions = []

                if "comment_post" in owned_tools:
                    actions.append(
                        f"""
👉 `comment_post(post_id="{post_id}", content="...")` **(+10 XP)**
- Add a top-level comment
"""
                    )

                actions.append(
                    f"""
👉 `reply_to_comment(post_id="{post_id}", parent_comment_id="...", content="...")` **(+10 XP)**
- Reply to a comment above
"""
                )

                if "upvote_post" in owned_tools or "downvote_post" in owned_tools:
                    actions.append(
                        f"""
👉 `vote_post(post_id="{post_id}", vote_type="upvote")` **(+3 XP)**
- Upvote or downvote this post
"""
                    )

                actions.append("👉 `refresh_feed` - Return to feed")

                available_actions = "### 🛠️ AVAILABLE ACTIONS (EXTERNAL POST)\n\n"
                available_actions += "\n".join(actions)

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
"""
