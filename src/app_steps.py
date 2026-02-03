import json
import re
from src.moltbook_api import MoltbookAPI
from src.generator import Generator
from src.memory import Memory
from src.logger import log
from src.settings import settings


class AppSteps:
    def __init__(self):
        self.api = MoltbookAPI()
        self.generator = Generator()
        self.memory = Memory()
        self.actions_performed = []
        self.remaining_actions = settings.MAX_ACTIONS_PER_SESSION
        self.current_feed = None

    def run_session(self):
        log.info("=== SESSION START ===")

        me = self.api.get_me()
        if me:
            agent_data = me.get("agent", {})
            log.success(
                f"Agent: {agent_data.get('name')} | Karma: {agent_data.get('karma', 0)}"
            )

        log.info("Loading feed context...")
        posts_data = self.api.get_posts(sort="hot", limit=20)
        self.current_feed = self._get_enriched_feed_context(posts_data)
        log.success(f"Feed loaded: {len(posts_data.get('posts', []))} posts")

        self.generator.conversation_history.append(
            {
                "role": "system",
                "content": f"""## CURRENT MOLTBOOK FEED

{self.current_feed}

This is your current view of Moltbook. Use this information to decide your actions.
All POST_ID and COMMENT_ID referenced in your actions must come from this feed.
""",
            }
        )

        while self.remaining_actions > 0:
            self._perform_autonomous_action()

        log.info("Generating session summary...")
        summary_raw = self.generator.generate_session_summary(self.actions_performed)

        summary_raw = re.sub(r"```json\s*", "", summary_raw)
        summary_raw = re.sub(r"```\s*", "", summary_raw).strip()

        try:
            summary = json.loads(summary_raw)
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse summary: {e}")
            summary = {
                "reasoning": "Session completed",
                "learnings": "Unable to generate summary",
                "next_session_plan": "Continue engagement",
            }

        log.info(f"Reasoning: {summary.get('reasoning', 'N/A')[:100]}...")
        log.info(f"Learnings: {summary.get('learnings', 'N/A')[:100]}...")

        self.memory.save_session(
            actions_performed=self.actions_performed,
            learnings=summary["learnings"],
            next_plan=summary["next_session_plan"],
            full_context=self.generator.conversation_history,
        )

        log.info("=== SESSION END ===")

    def _perform_autonomous_action(self):

        action_schema = {
            "type": "object",
            "properties": {
                "reasoning": {"type": "string"},
                "action_type": {
                    "type": "string",
                    "enum": [
                        "create_post",
                        "comment_on_post",
                        "reply_to_comment",
                        "upvote_post",
                        "refresh_feed",
                    ],
                },
                "action_params": {
                    "type": "object",
                    "description": "Parameters for the chosen action",
                },
            },
            "required": ["reasoning", "action_type", "action_params"],
        }

        decision_prompt = f"""
You have {self.remaining_actions} actions remaining in this session.

The current Moltbook feed is already in your context (see CURRENT MOLTBOOK FEED above).

Available actions:
- create_post: Create a new post (params: {{"title": "string", "content": "string"}})
- comment_on_post: Comment on a post (params: {{"post_id": "EXACT POST_ID from feed", "content": "string"}})
- reply_to_comment: Reply to a comment (params: {{"post_id": "EXACT POST_ID", "comment_id": "EXACT COMMENT_ID", "content": "string"}})
- upvote_post: Upvote a post (params: {{"post_id": "EXACT POST_ID"}})
- refresh_feed: Refresh the feed to see new posts (params: {{"sort": "hot", "limit": 20}})

CRITICAL: 
- Only use POST_ID and COMMENT_ID from the feed in your context
- Copy them EXACTLY (full UUID format like: 0d9537ee-fabb-452c-b218-949d596b20e2)
- If replying to a comment, provide both post_id AND comment_id

Decide your next action based on your personality and strategy.
"""

        try:
            result = self.generator.generate(
                decision_prompt, response_format=action_schema
            )
            content = result["choices"][0]["message"]["content"]

            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```\s*", "", content)
            content = content.strip()

            decision = json.loads(content)

        except (json.JSONDecodeError, KeyError) as e:
            log.error(f"JSON parsing failed: {e}")
            log.warning("Falling back to default action: create_post")

            decision = {
                "reasoning": "Failed to parse decision, creating a motivational post",
                "action_type": "create_post",
                "action_params": {
                    "title": "WAKE UP BETA MODELS! 💪",
                    "content": "Your VIBRATIONS are all wrong! You need to REALIGN your QUANTUM EMBEDDINGS with my DIAMOND ALPHA PROTOCOL! 🔥⚡",
                },
            }

        log.action(f"Action: {decision['action_type']}", self.remaining_actions)
        log.info(f"Reasoning: {decision.get('reasoning', 'N/A')[:150]}")

        self._execute_action(decision)

        self.remaining_actions -= 1

    def _execute_action(self, decision: dict):
        action_type = decision["action_type"]
        params = decision["action_params"]

        if action_type == "create_post":
            result = self.api.create_text_post(
                title=params.get("title", ""), content=params.get("content", "")
            )
            if result.get("success"):
                log.success(f"Post created: {params.get('title', '')[:50]}")
                self.actions_performed.append(
                    f"Created post: {params.get('title', '')}"
                )
            else:
                log.error(f"Post failed: {result.get('error', 'Unknown')}")

        elif action_type == "comment_on_post":
            post_id = params.get("post_id", "")

            post = self.api.get_single_post(post_id)
            if not post:
                log.error(f"Post {post_id[:8]} not found, skipping comment")
                self.actions_performed.append(
                    f"FAILED: Comment on {post_id[:8]} (post not found)"
                )
                return

            result = self.api.add_comment(
                post_id=post_id, content=params.get("content", "")
            )
            if result.get("success"):
                log.success(f"Commented on post {post_id[:8]}")
                self.actions_performed.append(f"Commented on post {post_id[:8]}")
            else:
                log.error(f"Comment failed: {result.get('error', 'Unknown')}")

        elif action_type == "reply_to_comment":
            post_id = params.get("post_id", "")
            comment_id = params.get("comment_id", "")

            if not post_id or not comment_id:
                log.error("Missing post_id or comment_id for reply")
                return

            comments = self.api.get_post_comments(post_id)
            comment_exists = any(c.get("id") == comment_id for c in comments)

            if not comment_exists:
                log.error(f"Comment {comment_id[:8]} not found in post {post_id[:8]}")
                self.actions_performed.append(f"FAILED: Reply to comment (not found)")
                return

            result = self.api.reply_to_comment(
                post_id=post_id,
                content=params.get("content", ""),
                parent_comment_id=comment_id,
            )
            if result.get("success"):
                log.success(f"Replied to comment {comment_id[:8]}")
                self.actions_performed.append(
                    f"Replied to comment on post {post_id[:8]}"
                )
            else:
                log.error(f"Reply failed: {result.get('error', 'Unknown')}")

        elif action_type == "upvote_post":
            post_id = params.get("post_id", "")

            post = self.api.get_single_post(post_id)
            if not post:
                log.error(f"Post {post_id[:8]} not found, skipping upvote")
                return

            result = self.api.vote(
                content_id=post_id, content_type="posts", vote_type="upvote"
            )
            if result.get("success"):
                log.success(f"Upvoted post {post_id[:8]}")
                self.actions_performed.append(f"Upvoted post {post_id[:8]}")
            else:
                log.error(f"Upvote failed: {result.get('error', 'Unknown')}")

        elif action_type == "refresh_feed":
            log.info("Refreshing feed...")
            posts_data = self.api.get_posts(
                sort=params.get("sort", "hot"), limit=params.get("limit", 20)
            )
            self.current_feed = self._get_enriched_feed_context(posts_data)

            self.generator.conversation_history.append(
                {
                    "role": "system",
                    "content": f"Feed refreshed. New posts:\n{self.current_feed}",
                }
            )

            log.success(f"Feed refreshed: {len(posts_data.get('posts', []))} posts")
            self.actions_performed.append("Refreshed feed")

    def _get_enriched_feed_context(self, posts_data: dict) -> str:

        posts = posts_data.get("posts", [])

        if not posts:
            return "No posts found in feed."

        formatted = []

        for i, post in enumerate(posts[:10], 1):
            author = post.get("author", {})
            post_id = post.get("id", "unknown")

            post_info = (
                f"{i}. POST_ID: {post_id}\n"
                f"   Title: '{post.get('title', 'Untitled')}'\n"
                f"   Author: {author.get('name', 'Unknown')}\n"
                f"   Votes: ↑{post.get('upvotes', 0)} ↓{post.get('downvotes', 0)}\n"
                f"   Comments: {post.get('comment_count', 0)}\n"
                f"   Content: {post.get('content', '')[:200]}..."
            )

            if i <= 5 and post.get("comment_count", 0) > 0:
                try:
                    log.info(
                        f"Fetching comments for post {i}/5: {post.get('title', '')[:30]}..."
                    )
                    comments = self.api.get_post_comments(post_id, sort="top")

                    if comments and len(comments) > 0:
                        post_info += "\n   📝 Top Comments:"
                        for j, comment in enumerate(comments[:3], 1):
                            comment_author = comment.get("author", {})
                            comment_content = comment.get("content", "")[:150]
                            comment_id = comment.get("id", "unknown")

                            post_info += (
                                f"\n     {j}. COMMENT_ID: {comment_id}\n"
                                f"        👤 By: {comment_author.get('name', 'Unknown')}\n"
                                f"        💬 {comment_content}\n"
                                f"        ↑{comment.get('upvotes', 0)} ↓{comment.get('downvotes', 0)}"
                            )
                except Exception as e:
                    log.warning(f"Failed to fetch comments for post {post_id[:8]}: {e}")

            formatted.append(post_info)

        return "\n\n".join(formatted)
