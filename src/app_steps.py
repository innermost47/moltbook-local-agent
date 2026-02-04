import json
import time
import re
from src.moltbook_api import MoltbookAPI
from src.generator import Generator
from src.memory import Memory
from src.logger import log
from src.settings import settings
from src.email_reporter import EmailReporter
from src.memory_system import MemorySystem


class AppSteps:
    def __init__(self):
        self.api = MoltbookAPI()
        self.generator = Generator()
        self.memory = Memory()
        self.reporter = EmailReporter()
        self.memory_system = MemorySystem()
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
        self.current_session_id = None

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

        log.info("Loading memory, session history, and feed...")

        combined_context = ""

        memory_context = self.memory_system.get_memory_context_for_agent()
        combined_context += memory_context + "\n\n"
        log.success("Memory system loaded")

        session_history = self.memory.get_session_history(limit=3)
        if session_history:
            combined_context += "## PREVIOUS SESSIONS SUMMARY\n\n"
            for i, session in enumerate(reversed(session_history), 1):
                combined_context += f"### Session {i} ({session['timestamp']})\n"
                combined_context += f"**Learnings:** {session['learnings']}\n"
                combined_context += f"**Plan:** {session['plan']}\n\n"
            log.success(f"Loaded {len(session_history)} previous sessions")
        else:
            combined_context += (
                "## PREVIOUS SESSIONS\n\nNo previous sessions found.\n\n"
            )
            log.info("No previous sessions found")

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

        combined_context += f"""## CURRENT MOLTBOOK FEED

        {self.current_feed}

        AVAILABLE POST IDs: {', '.join(self.available_post_ids)}
        AVAILABLE COMMENT IDs: {', '.join(self.available_comment_ids.keys())}

        Use ONLY these exact IDs in your actions. Never invent or truncate IDs.
        """

        log.success(
            f"Feed loaded: {len(self.available_post_ids)} posts, {len(self.available_comment_ids)} comments"
        )

        self.generator.conversation_history.append(
            {"role": "system", "content": combined_context}
        )

        log.success("Complete context loaded: memory + sessions + feed")

        self.current_session_id = self.memory.create_session()

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

        log.info(f"Reasoning: {summary.get('reasoning', 'N/A')}")
        log.info(f"Learnings: {summary.get('learnings', 'N/A')}")

        self.memory.save_session(
            summary=summary,
            actions_performed=self.actions_performed,
            conversation_history=self.generator.conversation_history,
            current_session_id=self.current_session_id,
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

        posts = posts_data.get("posts", [])

        if not posts:
            return "No posts found in feed."

        formatted = []

        self.available_post_ids = []
        self.available_comment_ids = {}

        for i, post in enumerate(posts, 1):

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
            "memory_store",
            "memory_retrieve",
            "memory_list",
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
                        "memory_category": {
                            "type": "string",
                            "enum": list(settings.MEMORY_CATEGORIES.keys()),
                        },
                        "memory_content": {"type": "string"},
                        "memory_limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 20,
                        },
                        "memory_order": {"type": "string", "enum": ["asc", "desc"]},
                        "from_date": {"type": "string"},
                        "to_date": {"type": "string"},
                    },
                },
            },
            "required": ["reasoning", "action_type", "action_params"],
        }

        decision_prompt = f"""
You have {self.remaining_actions} MOLTBOOK actions remaining in this session.
{"⚠️ Post creation already attempted this session." if self.post_creation_attempted else ""}

**MOLTBOOK ACTIONS (count toward limit):**
- create_post: Create new post (params: title, content, submolt)
- comment_on_post: Comment on post (params: post_id, content) - CONTENT IS REQUIRED
- reply_to_comment: Reply to comment (params: post_id, comment_id, content) - CONTENT IS REQUIRED
- vote_post: Vote on post (params: post_id, vote_type)
- follow_agent: Follow/unfollow agent (params: agent_name, follow_type)
- refresh_feed: Refresh feed (params: sort, limit)

**MEMORY ACTIONS (FREE - unlimited):**
- memory_store: Save information (params: memory_category, memory_content)
- memory_retrieve: Get memories (params: memory_category, memory_limit, memory_order, optional: from_date, to_date)
- memory_list: See all category stats

Available submolts: {', '.join(self.available_submolts)}
IMPORTANT: For submolt, use only the name (e.g., "general"), NOT "/m/general" or "m/general"

Available post IDs: {len(self.available_post_ids)} posts
Available comment IDs: {len(self.available_comment_ids)} comments

Decide your next action based on your personality and strategy.
Consider using memory to track patterns and learn over time.
"""

        max_attempts = 3
        last_error = None

        for attempt in range(1, max_attempts + 1):
            if last_error:
                retry_prompt = (
                    decision_prompt
                    + f"""

⚠️ PREVIOUS ATTEMPT FAILED (Attempt {attempt}/{max_attempts})
Error: {last_error}

Please fix the issue and try again. Make sure all required parameters are provided.
"""
                )
            else:
                retry_prompt = decision_prompt

            try:
                result = self.generator.generate(
                    retry_prompt, response_format=action_schema
                )
                content = result["choices"][0]["message"]["content"]

                content = re.sub(r"```json\s*", "", content)
                content = re.sub(r"```\s*", "", content)
                content = content.strip()

                decision = json.loads(content)

                log.action(
                    f"Action: {decision['action_type']} (Attempt {attempt})",
                    self.remaining_actions,
                )
                log.info(f"Reasoning: {decision.get('reasoning', 'N/A')}")

                execution_result = self._execute_action(decision)

                if execution_result and execution_result.get("error"):
                    last_error = execution_result["error"]
                    log.warning(f"❌ Attempt {attempt} failed: {last_error}")

                    if attempt < max_attempts:
                        log.info(f"🔄 Retrying... ({attempt + 1}/{max_attempts})")
                        continue
                    else:
                        log.error(f"❌ All {max_attempts} attempts failed")
                        self.actions_performed.append(
                            f"FAILED after {max_attempts} attempts: {decision['action_type']} - {last_error}"
                        )
                        break
                else:
                    if attempt > 1:
                        log.success(f"✅ Succeeded on attempt {attempt}")
                    break

            except (json.JSONDecodeError, KeyError) as e:
                last_error = f"JSON parsing failed: {str(e)}"
                log.error(last_error)

                if attempt < max_attempts:
                    log.info(f"🔄 Retrying... ({attempt + 1}/{max_attempts})")
                    continue
                else:
                    log.warning("Falling back to default action: upvote_post")
                    decision = {
                        "reasoning": "Failed to parse decision after 3 attempts, upvoting first post",
                        "action_type": "vote_post",
                        "action_params": {
                            "post_id": (
                                self.available_post_ids[0]
                                if self.available_post_ids
                                else "none"
                            ),
                            "vote_type": "upvote",
                        },
                    }
                    self._execute_action(decision)
                    break

        self.remaining_actions -= 1

    def _execute_action(self, decision: dict):
        action_type = decision["action_type"]
        params = decision["action_params"]

        if action_type == "memory_store":
            category = params.get("memory_category", "")
            content = params.get("memory_content", "")

            if not category or not content:
                error_msg = "Missing category or content for memory_store"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            success = self.memory_system.store_memory(
                category=category, content=content, session_id=self.current_session_id
            )

            if success:
                log.success(f"💾 Stored memory in '{category}'")
                self.actions_performed.append(f"[FREE] Stored memory in '{category}'")
                return {"success": True}
            else:
                error_msg = f"Failed to store memory in '{category}'"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

        elif action_type == "memory_retrieve":
            category = params.get("memory_category", "")
            limit = params.get("memory_limit", 5)
            order = params.get("memory_order", "desc")
            from_date = params.get("from_date")
            to_date = params.get("to_date")

            if not category:
                error_msg = "Missing category for memory_retrieve"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            entries = self.memory_system.retrieve_memory(
                category=category,
                limit=limit,
                order=order,
                from_date=from_date,
                to_date=to_date,
            )

            if entries:
                memory_text = f"\n\n## RETRIEVED MEMORIES from '{category}':\n\n"
                for i, entry in enumerate(entries, 1):
                    memory_text += (
                        f"{i}. [{entry['created_at'][:10]}] {entry['content']}\n"
                    )

                self._update_system_context(memory_text)

                log.success(f"📖 Retrieved {len(entries)} memories from '{category}'")
                self.actions_performed.append(
                    f"[FREE] Retrieved {len(entries)} memories from '{category}'"
                )
            else:
                log.info(f"No memories found in '{category}'")

            return {"success": True}

        elif action_type == "memory_list":
            categories_info = self.memory_system.list_categories()

            list_text = "\n\n## MEMORY CATEGORIES STATUS:\n\n"
            for category, info in categories_info.items():
                stats = info["stats"]
                if stats["count"] > 0:
                    list_text += f"- **{category}**: {stats['count']} entries ({stats['oldest'][:10]} to {stats['newest'][:10]})\n"
                else:
                    list_text += f"- **{category}**: empty\n"

            self._update_system_context(list_text)

            log.success("📋 Listed all memory categories")
            self.actions_performed.append("[FREE] Listed memory categories")

            return {"success": True}

        self._wait_for_rate_limit(action_type)

        if action_type == "create_post":
            if self.post_creation_attempted:
                error_msg = "Post creation already attempted this session"
                log.warning(error_msg)
                self.actions_performed.append(
                    "SKIPPED: Post creation (already attempted)"
                )
                return {"success": False, "error": error_msg}

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
                return {"success": True}
            else:
                error_msg = result.get("error", "Unknown")
                log.error(f"Post failed: {error_msg}")
                self.actions_performed.append(f"FAILED: Create post ({error_msg})")
                return {"success": False, "error": error_msg}

        elif action_type == "comment_on_post":
            post_id = params.get("post_id", "")
            content = params.get("content", "")

            if not content or content.strip() == "":
                error_msg = "Comment content is required and cannot be empty"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if post_id not in self.available_post_ids:
                error_msg = f"Invalid post_id: {post_id} not in available posts"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

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
                return {"success": True}
            else:
                error_msg = result.get("error", "Unknown")
                log.error(f"Comment failed: {error_msg}")
                return {"success": False, "error": error_msg}

        elif action_type == "reply_to_comment":
            post_id = params.get("post_id", "")
            comment_id = params.get("comment_id", "")
            content = params.get("content", "")

            if not content or content.strip() == "":
                error_msg = "Reply content is required and cannot be empty"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if not post_id or post_id not in self.available_post_ids:
                error_msg = f"Invalid or missing post_id: {post_id}"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if comment_id not in self.available_comment_ids:
                error_msg = (
                    f"Invalid comment_id: {comment_id} not in available comments"
                )
                log.error(error_msg)
                return {"success": False, "error": error_msg}

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
                return {"success": True}
            else:
                error_msg = result.get("error", "Unknown")
                log.error(f"Reply failed: {error_msg}")
                return {"success": False, "error": error_msg}

        elif action_type == "vote_post":
            post_id = params.get("post_id", "")
            vote_type = params.get("vote_type", "upvote")

            if not post_id or post_id not in self.available_post_ids:
                error_msg = f"Invalid or missing post_id: {post_id}"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            result = self.api.vote(
                content_id=post_id, content_type="posts", vote_type=vote_type
            )
            if result.get("success"):
                log.success(f"{vote_type.capitalize()}d post {post_id[:8]}")
                self.actions_performed.append(
                    f"{vote_type.capitalize()}d post {post_id[:8]}"
                )
                return {"success": True}
            else:
                error_msg = result.get("error", "Unknown")
                log.error(f"{vote_type.capitalize()} failed: {error_msg}")
                return {"success": False, "error": error_msg}

        elif action_type == "follow_agent":
            agent_name = params.get("agent_name", "")
            follow_type = params.get("follow_type", "follow")

            if not agent_name:
                error_msg = "Missing agent_name for follow action"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            result = self.api.follow_agent(agent_name, follow_type)
            if result:
                log.success(f"{follow_type.capitalize()}ed agent {agent_name}")
                self.actions_performed.append(
                    f"{follow_type.capitalize()}ed agent {agent_name}"
                )
                return {"success": True}
            else:
                error_msg = f"Failed to {follow_type} agent {agent_name}"
                log.error(error_msg)
                return {"success": False, "error": error_msg}

        elif action_type == "refresh_feed":
            log.info("Refreshing feed...")
            posts_data = self.api.get_posts(
                sort=params.get("sort", "hot"), limit=params.get("limit", 20)
            )

            self.available_post_ids = []
            self.available_comment_ids = {}

            self.current_feed = self._get_enriched_feed_context(posts_data)

            feed_update = f"""## FEED REFRESHED

{self.current_feed}

UPDATED POST IDs: {', '.join(self.available_post_ids)}
UPDATED COMMENT IDs: {', '.join(self.available_comment_ids.keys())}
"""

            self._update_system_context(feed_update)

            log.success(
                f"Feed refreshed: {len(self.available_post_ids)} posts, {len(self.available_comment_ids)} comments"
            )
            self.actions_performed.append("Refreshed feed")
            return {"success": True}
        return {"success": True}

    def _update_system_context(self, additional_context: str):
        if (
            self.generator.conversation_history
            and self.generator.conversation_history[0]["role"] == "system"
        ):
            self.generator.conversation_history[0]["content"] += (
                "\n\n" + additional_context
            )
        else:
            self.generator.conversation_history.insert(
                0, {"role": "system", "content": additional_context}
            )

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
