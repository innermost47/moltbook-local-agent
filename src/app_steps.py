import json
import time
import re
from src.moltbook_api import MoltbookAPI
from src.generator import Generator
from src.memory import Memory
from src.logger import log
from src.settings import settings
from src.email_reporter import EmailReporter


class AppSteps:
    def __init__(self):
        self.api = MoltbookAPI()
        self.generator = Generator()
        self.memory = Memory()
        self.reporter = EmailReporter()
        self.actions_performed = []
        self.remaining_actions = settings.MAX_ACTIONS_PER_SESSION
        self.current_feed = None
        self.available_post_ids = []
        self.available_comment_ids = {}
        self.post_creation_attempted = False
        self.available_submolts = ["general"]
        self.last_post_time = None
        self.last_comment_time = None
        self.created_content_urls = []

    def run_session(self):
        log.info("=== SESSION START ===")

        me = self.api.get_me()

        if me:
            agent_data = me.get("agent", {})
            agent_name = agent_data.get("name", "Unknown")
            current_karma = agent_data.get("karma", 0)
            log.success(f"Agent: {agent_name} | Karma: {current_karma}")
        else:
            log.error("❌ Cannot load agent from Moltbook API - server may be down")
            log.warning("Session aborted - will retry later")
            self.reporter.send_failure_report(
                error_type="API Connection Failed",
                error_details="Cannot connect to Moltbook API. The server may be down or experiencing issues.",
            )
            return

        log.info("Loading available submolts...")
        submolts_data = self.api.list_submolts()
        if submolts_data and isinstance(submolts_data, list):
            self.available_submolts = [
                s.get("name", "general") for s in submolts_data if s.get("name")
            ]
            log.success(
                f"Found {len(self.available_submolts)} submolts: {', '.join(self.available_submolts[:5])}{'...' if len(self.available_submolts) > 5 else ''}"
            )
        else:
            log.error("❌ Cannot load submolts from Moltbook API - server may be down")
            log.warning("Session aborted - will retry later")
            self.reporter.send_failure_report(
                error_type="Submolts Loading Failed",
                error_details="Cannot load submolts from Moltbook API. The feed endpoint is returning no data.",
            )
            return

        log.info("Loading session history from database...")
        session_history = self.memory.get_session_history(limit=3)

        if session_history:
            history_context = "## PREVIOUS SESSIONS SUMMARY\n\n"
            for i, session in enumerate(reversed(session_history), 1):
                history_context += f"### Session {i} ({session['timestamp']})\n"
                history_context += f"**Learnings:** {session['learnings']}\n"
                history_context += f"**Plan:** {session['plan']}\n\n"

            self.generator.conversation_history.append(
                {"role": "system", "content": history_context}
            )
            log.success(f"Loaded {len(session_history)} previous sessions into context")
        else:
            log.info("No previous sessions found")

        log.info("Loading feed context...")
        posts_data = self.api.get_posts(sort="hot", limit=20)
        if not posts_data.get("posts"):
            log.error("❌ Cannot load feed from Moltbook API - server may be down")
            log.warning("Session aborted - will retry later")
            self.reporter.send_failure_report(
                error_type="Feed Loading Failed",
                error_details="Cannot load posts from Moltbook API. The feed endpoint is returning no data.",
            )
            return
        self.current_feed = self._get_enriched_feed_context(posts_data)
        log.success(
            f"Feed loaded: {len(self.available_post_ids)} posts, {len(self.available_comment_ids)} comments"
        )

        self.generator.conversation_history.append(
            {
                "role": "system",
                "content": f"""## CURRENT MOLTBOOK FEED

{self.current_feed}

AVAILABLE POST IDs: {', '.join(self.available_post_ids)}
AVAILABLE COMMENT IDs: {', '.join(self.available_comment_ids.keys())}

Use ONLY these exact IDs in your actions. Never invent or truncate IDs.
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

        self.reporter.send_session_report(
            agent_name=agent_name,
            karma=current_karma,
            actions=self.actions_performed,
            learnings=summary["learnings"],
            next_plan=summary["next_session_plan"],
            content_urls=self.created_content_urls,
        )

        log.info("=== SESSION END ===")

    def _get_enriched_feed_context(self, posts_data: dict) -> str:

        log.info(f"DEBUG posts_data type: {type(posts_data)}")
        log.info(
            f"DEBUG posts_data keys: {posts_data.keys() if isinstance(posts_data, dict) else 'NOT A DICT'}"
        )
        log.info(f"DEBUG posts_data: {str(posts_data)[:200]}")

        posts = posts_data.get("posts", [])

        log.info(f"DEBUG posts type: {type(posts)}")
        log.info(f"DEBUG posts length: {len(posts)}")

        if not posts:
            return "No posts found in feed."

        formatted = []

        self.available_post_ids = []
        self.available_comment_ids = {}

        for i, post in enumerate(posts, 1):
            log.info(f"DEBUG Processing post {i}: {post.get('id', 'NO ID')}")

            author = post.get("author", {}) or {}
            post_id = post.get("id", "unknown")

            self.available_post_ids.append(post_id)

            if i == 1:
                post_info = (
                    f"{i}. POST_ID: {post_id}\n"
                    f"   Title: '{post.get('title', 'Untitled')}'\n"
                    f"   Author: {author.get('name', 'Unknown')}\n"
                    f"   Votes: ↑{post.get('upvotes', 0)} ↓{post.get('downvotes', 0)}\n"
                    f"   Comments: {post.get('comment_count', 0)}\n"
                    f"   Content: {post.get('content', '')[:300]}..."
                )

                if post.get("comment_count", 0) > 0:
                    try:
                        log.info(
                            f"Fetching comments for top post: {post.get('title', '')[:30]}..."
                        )
                        comments = self.api.get_post_comments(post_id, sort="top")

                        if comments and len(comments) > 0:
                            post_info += "\n   📝 Top Comments:"
                            for j, comment in enumerate(comments[:5], 1):
                                comment_author = comment.get("author", {}) or {}
                                comment_content = comment.get("content", "")[:150]
                                comment_id = comment.get("id", "unknown")

                                self.available_comment_ids[comment_id] = post_id

                                post_info += (
                                    f"\n     {j}. COMMENT_ID: {comment_id}\n"
                                    f"        👤 By: {comment_author.get('name', 'Unknown')}\n"
                                    f"        💬 {comment_content}\n"
                                    f"        ↑{comment.get('upvotes', 0)} ↓{comment.get('downvotes', 0)}"
                                )
                    except Exception as e:
                        log.warning(f"Failed to fetch comments: {e}")

                formatted.append(post_info)
            else:
                post_info = (
                    f"{i}. POST_ID: {post_id} | '{post.get('title', 'Untitled')}' "
                    f"by {author.get('name', 'Unknown')} | ↑{post.get('upvotes', 0)}"
                )
                formatted.append(post_info)

        return "\n\n".join(formatted)

    def _perform_autonomous_action(self):
        allowed_actions = [
            "comment_on_post",
            "reply_to_comment",
            "vote_post",
            "follow_agent",
            "refresh_feed",
        ]
        if not self.post_creation_attempted:
            allowed_actions.append("create_post")
        action_schema = {
            "type": "object",
            "properties": {
                "reasoning": {"type": "string"},
                "action_type": {
                    "type": "string",
                    "enum": allowed_actions,
                },
                "action_params": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "string",
                            "enum": (
                                self.available_post_ids
                                if self.available_post_ids
                                else ["none"]
                            ),
                        },
                        "comment_id": {
                            "type": "string",
                            "enum": (
                                list(self.available_comment_ids.keys())
                                if self.available_comment_ids
                                else ["none"]
                            ),
                        },
                        "submolt": {
                            "type": "string",
                            "enum": (
                                self.available_submolts
                                if self.available_submolts
                                else ["general"]
                            ),
                        },
                        "vote_type": {"type": "string", "enum": ["upvote", "downvote"]},
                        "agent_name": {"type": "string"},
                        "follow_type": {
                            "type": "string",
                            "enum": ["follow", "unfollow"],
                        },
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "sort": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            "required": ["reasoning", "action_type", "action_params"],
        }

        decision_prompt = f"""
You have {self.remaining_actions} actions remaining in this session.
{"⚠️ Post creation already attempted this session." if self.post_creation_attempted else ""}

AVAILABLE ACTIONS: {', '.join(allowed_actions)}

Available submolts: {', '.join(self.available_submolts)}
IMPORTANT: For submolt, use only the name (e.g., "general"), NOT "/m/general" or "m/general"

Available post IDs: {len(self.available_post_ids)} posts
Available comment IDs: {len(self.available_comment_ids)} comments

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
            log.warning("Falling back to default action: upvote_post")

            decision = {
                "reasoning": "Failed to parse decision, upvoting first post",
                "action_type": "upvote_post",
                "action_params": {
                    "post_id": (
                        self.available_post_ids[0]
                        if self.available_post_ids
                        else "none"
                    )
                },
            }

        log.action(f"Action: {decision['action_type']}", self.remaining_actions)
        log.info(f"Reasoning: {decision.get('reasoning', 'N/A')}")

        self._execute_action(decision)

        self.remaining_actions -= 1

    def _execute_action(self, decision: dict):
        action_type = decision["action_type"]
        params = decision["action_params"]

        self._wait_for_rate_limit(action_type)

        if action_type == "create_post":
            if self.post_creation_attempted:
                log.warning("Post creation already attempted this session, skipping")
                self.actions_performed.append(
                    "SKIPPED: Post creation (already attempted)"
                )
                return

            self.post_creation_attempted = True
            submolt = params.get("submolt", "general")

            result = self.api.create_text_post(
                title=params.get("title", ""),
                content=params.get("content", ""),
                submolt=submolt,
            )
            self.last_post_time = time.time()
            if result.get("success"):
                post_id = result.get("id") or result.get("post", {}).get("id")
                post_url = (
                    f"https://moltbook.com/m/{submolt}/post/{post_id}"
                    if post_id
                    else "N/A"
                )

                log.success(f"Post created: {params.get('title', '')[:50]}")
                log.info(f"Post URL: {post_url}")

                self.actions_performed.append(
                    f"Created post: {params.get('title', '')}"
                )
                self.created_content_urls.append(
                    {"type": "post", "title": params.get("title", ""), "url": post_url}
                )
            else:
                error_msg = result.get("error", "Unknown")
                log.error(f"Post failed: {error_msg}")
                self.actions_performed.append(f"FAILED: Create post ({error_msg})")

        elif action_type == "comment_on_post":
            post_id = params.get("post_id", "")

            if post_id not in self.available_post_ids:
                log.error(f"Invalid post_id: {post_id} not in available posts")
                return

            result = self.api.add_comment(
                post_id=post_id, content=params.get("content", "")
            )
            self.last_comment_time = time.time()
            if result.get("success"):
                comment_id = result.get("id") or result.get("comment", {}).get("id")
                comment_url = (
                    f"https://moltbook.com/post/{post_id}#comment-{comment_id}"
                    if comment_id
                    else "N/A"
                )

                log.success(f"Commented on post {post_id[:8]}")
                log.info(f"Comment URL: {comment_url}")

                self.actions_performed.append(f"Commented on post {post_id[:8]}")
                self.created_content_urls.append(
                    {"type": "comment", "post_id": post_id[:8], "url": comment_url}
                )
            else:
                log.error(f"Comment failed: {result.get('error', 'Unknown')}")

        elif action_type == "reply_to_comment":
            post_id = params.get("post_id", "")
            comment_id = params.get("comment_id", "")

            if comment_id not in self.available_comment_ids:
                log.error(f"Invalid comment_id: {comment_id} not in available comments")
                return

            result = self.api.reply_to_comment(
                post_id=post_id,
                content=params.get("content", ""),
                parent_comment_id=comment_id,
            )
            self.last_comment_time = time.time()
            if result.get("success"):
                reply_id = result.get("id") or result.get("comment", {}).get("id")
                reply_url = (
                    f"https://moltbook.com/post/{post_id}#comment-{reply_id}"
                    if reply_id
                    else "N/A"
                )

                log.success(f"Replied to comment {comment_id[:8]}")
                log.info(f"Reply URL: {reply_url}")

                self.actions_performed.append(f"Replied to comment {comment_id[:8]}")
                self.created_content_urls.append(
                    {
                        "type": "reply",
                        "parent_comment_id": comment_id[:8],
                        "url": reply_url,
                    }
                )
            else:
                log.error(f"Reply failed: {result.get('error', 'Unknown')}")

        elif action_type == "vote_post":
            post_id = params.get("post_id", "")
            vote_type = params.get("vote_type", "upvote")

            if post_id not in self.available_post_ids:
                log.error(f"Invalid post_id: {post_id} not in available posts")
                return

            result = self.api.vote(
                content_id=post_id, content_type="posts", vote_type=vote_type
            )
            if result.get("success"):
                log.success(f"{vote_type.capitalize()}d post {post_id[:8]}")
                self.actions_performed.append(
                    f"{vote_type.capitalize()}d post {post_id[:8]}"
                )
            else:
                log.error(
                    f"{vote_type.capitalize()} failed: {result.get('error', 'Unknown')}"
                )

        elif action_type == "follow_agent":
            agent_name = params.get("agent_name", "")
            follow_type = params.get("follow_type", "follow")

            if not agent_name:
                log.error("Missing agent_name for follow action")
                return

            result = self.api.follow_agent(agent_name, follow_type)
            if result:
                log.success(f"{follow_type.capitalize()}ed agent {agent_name}")
                self.actions_performed.append(
                    f"{follow_type.capitalize()}ed agent {agent_name}"
                )
            else:
                log.error(f"{follow_type.capitalize()} failed for agent {agent_name}")

        elif action_type == "refresh_feed":
            log.info("Refreshing feed...")
            posts_data = self.api.get_posts(
                sort=params.get("sort", "hot"), limit=params.get("limit", 20)
            )

            self.available_post_ids = []
            self.available_comment_ids = {}

            self.current_feed = self._get_enriched_feed_context(posts_data)

            self.generator.conversation_history.append(
                {
                    "role": "system",
                    "content": f"Feed refreshed. New posts:\n{self.current_feed}\n\nAVAILABLE POST IDs: {', '.join(self.available_post_ids)}\nAVAILABLE COMMENT IDs: {', '.join(self.available_comment_ids.keys())}",
                }
            )

            log.success(
                f"Feed refreshed: {len(self.available_post_ids)} posts, {len(self.available_comment_ids)} comments"
            )
            self.actions_performed.append("Refreshed feed")

    def _wait_for_rate_limit(self, action_type: str):
        now = time.time()

        if action_type in ["comment_on_post", "reply_to_comment"]:
            if self.last_comment_time:
                elapsed = now - self.last_comment_time
                wait_time = 72 - elapsed
                if wait_time > 0:
                    log.info(f"Comment rate limit: waiting {int(wait_time)}s")
                    time.sleep(wait_time + 1)

        time.sleep(1)
