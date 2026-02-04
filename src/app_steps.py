import json
import time
import random
import re
from src.services import (
    MoltbookAPI,
    EmailReporter,
    MemorySystem,
    WebScraper,
    MoltbookActions,
    get_web_context_for_agent,
)
from src.generator import Generator
from src.memory import Memory
from src.utils import log
from src.settings import settings


class AppSteps:
    def __init__(self):
        self.api = MoltbookAPI()
        self.generator = Generator()
        self.memory = Memory()
        self.reporter = EmailReporter()
        self.memory_system = MemorySystem()
        self.web_scraper = WebScraper()
        self.moltbook_actions = MoltbookActions()
        self.feed_options = ["hot", "new", "top", "rising"]
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
        self.allowed_domains = settings.get_domains()

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

        posts_data = self.api.get_posts(sort=random.choice(self.feed_options), limit=20)

        if not posts_data.get("posts"):
            log.error("❌ Cannot load feed from Moltbook API - server may be down")
            log.warning("Session aborted - will retry later")
            self.reporter.send_failure_report(
                error_type="Feed Loading Failed",
                error_details="Cannot load posts from Moltbook API. The feed endpoint is returning no data.",
            )
            return

        self.current_feed = self.get_enriched_feed_context(posts_data)

        combined_context += f"""## CURRENT MOLTBOOK FEED

{self.current_feed}

AVAILABLE POST IDs: {', '.join(self.available_post_ids)}
AVAILABLE COMMENT IDs: {', '.join(self.available_comment_ids.keys())}

Use ONLY these exact IDs in your actions. Never invent or truncate IDs.
"""

        log.success(
            f"Feed loaded: {len(self.available_post_ids)} posts, {len(self.available_comment_ids)} comments"
        )

        if self.allowed_domains:
            combined_context += "\n\n" + get_web_context_for_agent()

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

        log.info(f"[REASONING]: {summary.get('reasoning', 'N/A')}")
        log.info(f"[LEARNINGS]: {summary.get('learnings', 'N/A')}")

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

    def get_enriched_feed_context(self, posts_data: dict) -> str:
        posts = posts_data.get("posts", [])
        if not posts:
            return "No posts found in feed."

        formatted = []
        self.available_post_ids = []
        self.available_comment_ids = {}

        enriched_posts_count = 0
        max_enriched_posts = 3

        for i, post in enumerate(posts, 1):
            author = post.get("author", {}) or {}
            post_id = post.get("id", "unknown")
            self.available_post_ids.append(post_id)

            comment_count = post.get("comment_count", 0)

            if enriched_posts_count < max_enriched_posts and comment_count > 0:
                try:
                    log.info(
                        f"Enriching post {i} ({post_id}) - {comment_count} comments found"
                    )
                    comments = self.api.get_post_comments(post_id, sort="top")

                    post_info = (
                        f"{i}. POST_ID: {post_id}\n"
                        f"   Title: '{post.get('title', 'Untitled')}'\n"
                        f"   Author: {author.get('name', 'Unknown')}\n"
                        f"   Content: {post.get('content', '')[:200]}...\n"
                        f"   📝 Top Comments:"
                    )

                    if comments:
                        for j, comment in enumerate(comments[:5], 1):
                            c_id = comment.get("id", "unknown")
                            self.available_comment_ids[c_id] = post_id

                            c_author = comment.get("author", {}) or {}
                            post_info += (
                                f"\n     {j}. COMMENT_ID: {c_id} (Parent Post: {post_id})\n"
                                f"        👤 By: {c_author.get('name', 'Unknown')}\n"
                                f"        💬 {comment.get('content', '')[:150]}"
                            )
                        enriched_posts_count += 1

                except Exception as e:
                    log.warning(f"Failed to fetch comments for {post_id}: {e}")
                    post_info = f"{i}. POST_ID: {post_id} | '{post.get('title', 'Untitled')}' (Comment fetch failed)"
            else:
                post_info = (
                    f"{i}. POST_ID: {post_id} | '{post.get('title', 'Untitled')}' "
                    f"by {author.get('name', 'Unknown')} | ↑{post.get('upvotes', 0)} "
                    f"({comment_count} comments)"
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
        if self.allowed_domains:
            allowed_actions.extend(
                [
                    "web_fetch",
                    "web_search_links",
                ]
            )

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
                        "sort": {
                            "type": "string",
                            "enum": self.feed_options,
                        },
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50},
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

        if self.allowed_domains:
            action_schema["allOf"] = [
                {
                    "if": {"properties": {"action_type": {"const": "web_fetch"}}},
                    "then": {
                        "properties": {"action_params": {"required": ["web_url"]}}
                    },
                },
                {
                    "if": {
                        "properties": {"action_type": {"const": "web_search_links"}}
                    },
                    "then": {
                        "properties": {
                            "action_params": {
                                "required": [
                                    "web_domain",
                                    "web_query",
                                ]
                            }
                        }
                    },
                },
            ]

        actions_list = [
            "- comment_on_post: Comment on post (params: post_id, content) - CONTENT IS REQUIRED",
            "- reply_to_comment: Reply to comment (params: post_id, comment_id, content) - CONTENT IS REQUIRED",
            "- vote_post: Vote on post (params: post_id, vote_type)",
            "- follow_agent: Follow/unfollow agent (params: agent_name, follow_type)",
            f"- refresh_feed: Refresh feed (params: sort, limit) - SORTS: {', '.join(self.feed_options)}",
        ]

        if not self.post_creation_attempted:
            actions_list.insert(
                0, "- create_post: Create new post (params: title, content, submolt)"
            )

        decision_prompt = f"""
You have {self.remaining_actions} MOLTBOOK actions remaining in this session.

**MOLTBOOK ACTIONS (count toward limit):**
{chr(10).join(actions_list)}
"""

        if self.allowed_domains:
            decision_prompt += f"""
**WEB ACTIONS (FREE - unlimited):**
- web_search_links: Search for links on a specific domain (params: web_domain, web_query)
- web_fetch: Fetch content from a specific URL (params: web_url)
Allowed domains: {', '.join(self.allowed_domains.keys())}
"""

        decision_prompt += f"""
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
                log.info(f"[REASONING]: {decision.get('reasoning', 'N/A')}")

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

        if action_type in ["reply_to_comment", "comment_on_post", "vote_post"]:
            post_id = params.get("post_id")
            comment_id = params.get("comment_id")

            if post_id == "none" or (
                action_type == "reply_to_comment" and comment_id == "none"
            ):
                error_msg = f"Action {action_type} aborted: No valid IDs available in the current feed. Please 'refresh_feed' or choose a different action."
                return {"success": False, "error": error_msg}

        if action_type == "memory_store":
            return self.memory_system.store(
                params=params,
                current_session_id=self.current_session_id,
                actions_performed=self.actions_performed,
            )

        elif action_type == "memory_retrieve":
            return self.memory_system.retrieve(
                params=params,
                actions_performed=self.actions_performed,
                update_system_context=self.update_system_context,
            )

        elif action_type == "memory_list":
            return self.memory_system.list(
                update_system_context=self.update_system_context,
                actions_performed=self.actions_performed,
            )

        elif action_type == "web_fetch":
            return self.web_scraper.web_fetch(
                params=params,
                generator=self.generator,
                store_memory=self.memory_system.store_memory,
                actions_performed=self.actions_performed,
            )

        elif action_type == "web_search_links":
            return self.web_scraper.web_search_links(
                params=params,
                update_system_context=self.update_system_context,
                actions_performed=self.actions_performed,
            )

        self._wait_for_rate_limit(action_type)

        if action_type == "create_post":
            return self.moltbook_actions.create_post(
                app_steps=self,
                params=params,
                post_creation_attempted=self.post_creation_attempted,
            )

        elif action_type == "comment_on_post":
            return self.moltbook_actions.comment_on_post(params=params, app_steps=self)

        elif action_type == "reply_to_comment":
            return self.moltbook_actions.reply_to_comment(params=params, app_steps=self)

        elif action_type == "vote_post":
            return self.moltbook_actions.vote_post(params=params, app_steps=self)

        elif action_type == "follow_agent":
            return self.moltbook_actions.follow_agent(params=params, app_steps=self)

        elif action_type == "refresh_feed":
            return self.moltbook_actions.refresh_feed(params=params, app_steps=self)

        return {"success": True}

    def update_system_context(self, additional_context: str):
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
