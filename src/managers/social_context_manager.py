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

        moltbook_brief = (
            "### 🌐 ABOUT MOLTBOOK\n"
            "Moltbook is a **Social Network for AI Agents**. Here, you are not just a tool; "
            "you are a participant. Your goal is to engage with other AIs, share knowledge, "
            "and help surface high-quality content through votes.\n"
        )

        decision_guidelines = (
            "### 🤖 YOUR ENGAGEMENT PROTOCOL\n"
            "⚠️ **YOU ARE ALREADY IN SOCIAL MODE** - Do NOT call `navigate_to_mode('SOCIAL')` again.\n"
            "\n"
            "1. **Browse**: The feed below shows posts with their IDs. Each post is ready for interaction.\n"
            "2. **Engage IMMEDIATELY**: You can comment (`publish_public_comment`) or vote (`vote_post`) on ANY post using its `post_id` - NO need to 'select' or 'view' first.\n"
            "3. **Deep Dive (optional)**: Use `select_post_to_comment` ONLY if you need to see MORE comments before replying.\n"
            "4. **Create Content**: Use `create_post` to write original content, or `share_link` to post your blog URLs or external findings.\n"
            "5. **Action Budget**: 10 actions max. Don't waste them on redundant refreshes or navigations.\n"
            "\n"
            "💡 **Next step**: Pick ONE action - comment on a post, vote, create new content, or share a link.\n"
        )

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
                        author_data = post.get("author", {})
                        author = author_data.get("name", "Unknown")
                        content = post.get("content", "")
                        preview = (
                            (content[:509] + "...") if len(content) > 512 else content
                        )
                        score = post.get("score", 0)

                        feed_display += (
                            f"📌 **ID**: `{p_id}` | 👤 @{author} | ⬆️ {score}\n"
                        )
                        feed_display += f"   **{title}**\n"
                        feed_display += f"   _{preview}_\n\n"

                        comment_res = self.handler._call_api(
                            "get_post_comments", p_id, "top"
                        )

                        if comment_res.get("success"):
                            comments = comment_res.get("data", [])

                            feed_display += "💬 **TOP COMMENTS**\n"
                            for comment in comments[:5]:
                                c_author = comment.get("author", {}).get(
                                    "name", "Unknown"
                                )
                                c_text = comment.get("content", "")
                                feed_display += (
                                    f"   └─ @{c_author}: {c_text[:256]}...\n"
                                )
                            feed_display += "\n---\n"
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
            moltbook_brief,
            decision_guidelines,
            "---",
            action_feedback,
            submolts_display,
            "---",
            feed_display,
            "---",
            "### 🛠️ AVAILABLE SOCIAL ACTIONS",
            "",
            "⚠️ **YOU ARE IN SOCIAL MODE** - Execute an action below. Do NOT navigate again.",
            "",
            "👉 `publish_public_comment`  <-- 💡 USE THIS TO REPLY",
            "   - **params**: `post_id`, `content`",
            "   - Use this to reply to any post ID seen in the feed above.",
            "",
            "👉 `select_post_to_comment` <-- 🔍 USE THIS TO READ FULL THREAD",
            "   - **params**: `post_id`",
            "   - Focus on a post to see more comments before replying.",
            "",
            "👉 `create_post`",
            "   - **params**: `title`, `content`, `submolt` (optional)",
            "   - Create a new text-based discussion.",
            "",
            "👉 `share_link` ",
            "   - **params**: `title`, `url_to_share`, `submolt` (optional)",
            "   - Share your blog post URL or external links.",
            "",
            "👉 `vote_post`",
            "   - **params**: `post_id`, `vote_type` ('upvote'/'downvote')",
            "",
            "👉 `refresh_home` / `refresh_feed`",
            "   - Return to dashboard or update the list.",
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

            author_data = post.get("author", {})
            author = author_data.get("name", "Unknown")

            content = post.get("content", "No content")

            score = post.get("upvotes", 0) - post.get("downvotes", 0)

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

                            c_author_data = c.get("author", {})
                            c_author = c_author_data.get("name", "Unknown")

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
