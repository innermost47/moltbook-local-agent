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
    BlogActions,
    get_web_context_for_agent,
)
from src.generator import Generator
from src.memory import Memory
from src.utils import log
from src.settings import settings
from src.services.planning_system import PlanningSystem
from src.schemas import (
    master_plan_schema,
    session_plan_schema,
    summary_schema,
    update_master_plan_schema,
    get_actions_schema,
)


class AppSteps:
    def __init__(self):
        self.api = MoltbookAPI()
        self.generator = Generator()
        self.memory = Memory()
        self.reporter = EmailReporter()
        self.memory_system = MemorySystem()
        self.planning_system = PlanningSystem(db_path=settings.DB_PATH)
        self.web_scraper = WebScraper()
        self.moltbook_actions = MoltbookActions(db_path=settings.DB_PATH)
        self.blog_actions = BlogActions() if settings.BLOG_API_URL else None
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
        self.session_todos = []
        self.blog_article_attempted = False
        self.current_prompt = None
        self.master_plan_success_prompt = None

    def run_session(self):
        log.info("=== SESSION START ===")
        combined_context, agent_name, current_karma = self.get_context()
        self.generator.conversation_history.append(
            {
                "role": "system",
                "content": self.generator.get_main_system_prompt()
                + f"\n\n{combined_context}",
            }
        )

        log.success("Complete context loaded: planning + memory + sessions + feed")

        self.current_session_id = self.memory.create_session()
        if not self._ensure_master_plan():
            combined_context, agent_name, current_karma = self.get_context()
            self.generator.conversation_history[0] = {
                "role": "system",
                "content": self.generator.get_main_system_prompt()
                + f"\n\n{combined_context}",
            }
        self._create_session_plan()
        pending_confirmation = "✅ SESSION PLAN LOADED.\n"
        pending_confirmation += (
            f"Tasks: {', '.join([t['task'] for t in self.session_todos])}\n\n"
        )
        while self.remaining_actions > 0:
            pending_confirmation = self._perform_autonomous_action(
                extra_feedback=pending_confirmation
            )
            if pending_confirmation and "TERMINATE_SESSION" in pending_confirmation:
                log.info("Agent decided to terminate session early.")
                break

        log.info("Generating session summary...")

        self.current_prompt = f"""
        Session completed. Here's what happened:

        Actions performed: {len(self.actions_performed)}
        {chr(10).join(f"- {action}" for action in self.actions_performed)}

        Reflect on this session and create a summary with:
        1. Your reasoning about what worked/didn't work
        2. Key learnings from user interactions
        3. Your strategic plan for the next session
        """
        summary_raw = self.generator.generate_session_summary(
            self.current_prompt, summary_schema
        )

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

        self._update_master_plan_if_needed(summary)

        self.reporter.send_session_report(
            agent_name=agent_name,
            karma=current_karma,
            actions=self.actions_performed,
            learnings=summary["learnings"],
            next_plan=summary["next_session_plan"],
            content_urls=self.created_content_urls,
        )

        log.info("=== SESSION END ===")

    def get_context(self):
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
            all_submolts = [
                s.get("name", "general") for s in submolts_data if s.get("name")
            ]
            if "general" in all_submolts:
                all_submolts.remove("general")
                sample_size = min(len(all_submolts), 19)
                self.available_submolts = ["general"] + random.sample(
                    all_submolts, sample_size
                )
            else:
                sample_size = min(len(all_submolts), 20)
                self.available_submolts = random.sample(all_submolts, sample_size)

            log.success(
                f"Sampled {len(self.available_submolts)} random submolts for GBNF stability."
            )
        else:
            log.error("❌ Cannot load submolts from Moltbook API - server may be down")
            log.warning("Session aborted - will retry later")
            self.reporter.send_failure_report(
                error_type="Submolts Loading Failed",
                error_details="Cannot load submolts from Moltbook API. The feed endpoint is returning no data.",
            )
            return

        log.info("Loading memory, planning context, session history, and feed...")

        combined_context = ""

        planning_context = self.planning_system.get_planning_context()
        combined_context += planning_context + "\n\n"
        log.success("Planning context loaded")

        memory_context = self.memory_system.get_memory_context_for_agent()
        combined_context += memory_context + "\n\n"
        log.success("Memory system loaded")

        session_history = self.memory.get_session_history(limit=3)
        if session_history:
            combined_context += "## 📝 PREVIOUS SESSIONS SUMMARY\n\n"
            for i, session in enumerate(reversed(session_history), 1):
                combined_context += f"### Session {i} ({session['timestamp']})\n"
                combined_context += f"**Learnings:** {session['learnings']}\n"
                combined_context += f"**Plan:** {session['plan']}\n\n"
            combined_context += f"\n\n---  \n\n"
            log.success(f"Loaded {len(session_history)} previous sessions")
        else:
            combined_context += (
                "## PREVIOUS SESSIONS\n\nNo previous sessions found.\n\n---  \n\n"
            )
            log.info("No previous sessions found")

        if self.blog_actions:
            log.info("Synchronizing blog catalog...")
            try:
                existing_articles = self.blog_actions.list_articles()

                if existing_articles and isinstance(existing_articles, list):
                    published_titles = [
                        post.get("title", "Untitled") for post in existing_articles
                    ][:10]

                    blog_knowledge = "## 📚 PREVIOUSLY PUBLISHED BLOG ARTICLES\n"
                    blog_knowledge += "- " + "\n- ".join(published_titles) + "\n"
                    blog_knowledge += "\n**♟️ STRATEGIC INSTRUCTION: Do not duplicate existing topics. Always provide a new angle or a superior technical perspective.**\n\n--- \n\n"

                    combined_context += blog_knowledge
                    log.success(
                        f"Blog synchronized: {len(published_titles)} articles found."
                    )
                else:
                    log.info(
                        "Blog catalog is empty. Ready for initial content injection."
                    )

                log.info("Checking pending comment key requests...")
                pending_keys = self.blog_actions.review_comment_key_requests(self)

                if pending_keys.get("success") and pending_keys.get("count", 0) > 0:
                    key_context = "\n## 🔑 PENDING COMMENT KEY REQUESTS\n\n"
                    requests_to_process = pending_keys.get("requests", [])[:10]
                    for req in requests_to_process:
                        key_context += f"- **Request ID**: `{req['request_id']}`\n"
                        key_context += f"  - Agent: {req['agent_name']}\n"
                        key_context += (
                            f"  - Description: {req.get('agent_description', 'N/A')}\n"
                        )
                        key_context += f"  - Email: {req.get('contact_email', 'N/A')}\n"
                        key_context += f"  - Date: {req['created_at']}\n\n"

                    combined_context += key_context
                    log.success(
                        f"Found {pending_keys['count']} pending comment key requests"
                    )
                else:
                    log.info("No pending comment key requests")

            except Exception as e:
                log.error(f"Failed to synchronize blog: {e}")

        last_todos = self.planning_system.get_last_session_todos()
        if last_todos:
            combined_context += "## 📋 LAST SESSION TO-DO LIST\n\n"
            for todo in last_todos:
                combined_context += f"✅ {todo['task']}\n"
            combined_context += "\n"
            log.success(f"Loaded {len(last_todos)} todos from last session")

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

        combined_context += f"""## 🦞 CURRENT MOLTBOOK FEED

{self.current_feed}

**🚨 USE ONLY THESE EXACT IDS IN YOUR ACTIONS. NEVER INVENT OR TRUNCATE IDS.**

---  

"""

        log.success(
            f"Feed loaded: {len(self.available_post_ids)} posts, {len(self.available_comment_ids)} comments"
        )

        if self.allowed_domains:
            combined_context += "\n\n" + get_web_context_for_agent()

        combined_context += "\n\n" + self.get_instruction_default()

        return combined_context, agent_name, current_karma

    def _ensure_master_plan(self):
        current_plan = self.planning_system.get_active_master_plan()

        if not current_plan:
            log.warning("No Master Plan found. Forcing initialization...")

            init_prompt = f"""
You are starting your first session without a Master Plan.
Based on your persona and the current state of Moltbook, define your long-term objective.
"""

            try:
                result = self.generator.generate(
                    init_prompt, response_format=master_plan_schema
                )
                content = re.sub(
                    r"```json\s*|```\s*", "", result["choices"][0]["message"]["content"]
                ).strip()
                plan_data = json.loads(content)

                self.planning_system.create_or_update_master_plan(
                    objective=plan_data.get("objective"),
                    strategy=plan_data.get("strategy"),
                    milestones=plan_data.get("milestones", []),
                )

                self.master_plan_success_prompt = "✅ MASTER PLAN INITIALIZED: Your supreme goal and strategy are now active.\n"

                log.success(f"Master Plan initialized: {plan_data.get('objective')}")
                return False
            except Exception as e:
                log.error(f"Failed to initialize Master Plan: {e}")
                return True
        else:
            self.master_plan_success_prompt = ""
            return True

    def _create_session_plan(self):
        log.info("Creating session plan...")

        self.current_prompt = f"""{getattr(self, 'master_plan_success_prompt', '')}
Based on your master plan, previous sessions, current context, and feed state,
create a concrete to-do list for THIS session.

Generate 3-5 specific, actionable tasks prioritized by importance (1-5, 5 being highest).
"""

        try:
            result = self.generator.generate(self.current_prompt, session_plan_schema)
            content = result["choices"][0]["message"]["content"]

            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```\s*", "", content).strip()

            plan_data = json.loads(content)

            log.info(f"[PLAN REASONING]: {plan_data.get('reasoning', 'N/A')}")

            tasks = plan_data.get("tasks", [])
            if tasks:
                log.info(f"Session TO-DO LIST:")
                for i, task in enumerate(tasks, 1):
                    priority = "⭐" * task.get("priority", 1)
                    log.info(f"  {i}. [{priority}] {task.get('task')}")

                self.planning_system.create_session_todos(
                    session_id=self.current_session_id, tasks=tasks
                )

                self.session_todos = tasks

                todo_context = "\n\n## 📋 YOUR SESSION TO-DO LIST\n\n"
                for task in tasks:
                    todo_context += f"- [{task.get('priority')}] {task.get('task')}\n"
                todo_context += (
                    "\nRemember to mark tasks as completed when you accomplish them!\n"
                )
                self.current_prompt = todo_context

        except Exception as e:
            log.error(f"Failed to create session plan: {e}")

    def _update_master_plan_if_needed(self, summary: dict):

        current_plan = self.planning_system.get_active_master_plan()

        plan_json = (
            json.dumps(current_plan, indent=2) if current_plan else "NO MASTER PLAN YET"
        )

        self.current_prompt = f"""
Based on this session's learnings and your current master plan:

### 🗺️ CURRENT MASTER PLAN
{plan_json}

### 💡 SESSION LEARNINGS
{summary.get('learnings', 'N/A')}

Should you update your master plan? Consider:
- Have you achieved a major milestone?
- Have you learned something that changes your strategy?
- Do you need to refine your objective?
"""

        try:
            result = self.generator.generate(
                self.current_prompt, update_master_plan_schema
            )
            content = result["choices"][0]["message"]["content"]

            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```\s*", "", content).strip()

            decision = json.loads(content)

            if decision.get("should_update"):
                log.info(f"Updating master plan: {decision.get('reasoning')}")

                self.planning_system.create_or_update_master_plan(
                    objective=decision.get("new_objective"),
                    strategy=decision.get("new_strategy"),
                    milestones=decision.get("new_milestones", []),
                )
            else:
                log.info(f"Master plan unchanged: {decision.get('reasoning')}")

        except Exception as e:
            log.error(f"Failed to evaluate master plan update: {e}")

    def get_enriched_feed_context(self, posts_data: dict) -> str:
        posts_list = []
        if isinstance(posts_data, dict):
            posts_list = posts_data.get("posts", posts_data.get("data", []))
            if not posts_list and len(posts_data) > 0:
                log.warning(f"Unrecognized dict structure: {posts_data.keys()}")
        elif isinstance(posts_data, list):
            posts_list = posts_data

        if not posts_list:
            return "Feed is currently empty."

        MAX_POSTS = 6
        MAX_COMMENTS_PER_POST = 3
        CONTENT_TRUNC = 350
        COMMENT_TRUNC = 150

        formatted = []
        self.available_post_ids = []
        self.available_comment_ids = {}

        for i, post in enumerate(posts_list[:MAX_POSTS], 1):
            try:
                if post is None or not isinstance(post, dict):
                    continue
                p_id = post.get("id", "unknown")
                self.available_post_ids.append(p_id)

                author_name = post.get("author", {}).get("name", "Unknown")
                comment_count = post.get("comment_count", 0)

                post_block = (
                    f"=== {i}. POST_ID: {p_id} ===\n"
                    f"   Title: {post.get('title', 'Untitled')}\n"
                    f"   Author: {author_name} | Upvotes: {post.get('upvotes', 0)}\n"
                    f"   Content: {post.get('content', '')[:CONTENT_TRUNC]}\n\n"
                    f"   Total Comments: {comment_count}\n\n"
                )

                if comment_count > 0:
                    try:
                        comments = self.api.get_post_comments(p_id, sort="top")

                        if comments:
                            post_block += f"   📝 TOP {len(comments[:MAX_COMMENTS_PER_POST])} COMMENTS (Selected for analysis):\n"
                            for j, comment in enumerate(
                                comments[:MAX_COMMENTS_PER_POST], 1
                            ):
                                c_id = comment.get("id", "unknown")
                                self.available_comment_ids[c_id] = p_id
                                c_author = comment.get("author", {}).get(
                                    "name", "Unknown"
                                )

                                post_block += (
                                    f"      ├── {j}. COMMENT_ID: {c_id}\n"
                                    f"      │   By: {c_author}\n"
                                    f"      │   Text: {comment.get('content', '')[:COMMENT_TRUNC]}\n"
                                    f"      │\n"
                                )
                    except Exception as e:
                        log.warning(f"Could not sync comments for {p_id}: {e}")

                formatted.append(post_block + "\n\n---  \n\n")
            except Exception as e:
                log.warning(f"Could not sync post for post_id {p_id}: {e}")

        return "\n\n".join(formatted)

    def get_instruction_default(self):
        actions_list = [
            "- comment_on_post: (params: post_id, content) - CONTENT IS MANDATORY",
            "- reply_to_comment: (params: post_id, comment_id, content) - CONTENT IS MANDATORY",
            "- vote_post: (params: post_id, vote_type)",
            "- share_link: (params: url) - Share an external URL",
            "- follow_agent: (params: agent_name, follow_type)",
            f"- refresh_feed: (params: sort, limit) - SORTS: {', '.join(self.feed_options)}",
            "- create_post: (params: title, content, submolt) - FULL TEXT REQUIRED IN CONTENT",
        ]

        submolts_formatted = chr(10).join([f"- {s}" for s in self.available_submolts])

        decision_prompt = f"""
### 🛑 SESSION CONSTRAINTS
- **Quota**: EVERY action costs 1 point. No exceptions.
- **Moltbook Posts**: Only 1 `create_post` allowed per session.
- **Blog Articles**: Only 1 `write_blog_article` allowed per session.
- **Dynamic Status**: Check the icons above in each turn. If it shows ❌, you MUST NOT use that action again.

---  

**📌 MOLTBOOK ACTIONS:**
{chr(10).join(actions_list)}
"""

        if self.allowed_domains:
            decision_prompt += f"""
**📌 WEB ACTIONS:**
- web_scrap_for_links: Search for links on a specific domain (params: web_domain, web_query)
- web_fetch: Fetch content from a specific URL (params: web_url)
Allowed domains: {', '.join(self.allowed_domains.keys())}
"""
        if self.blog_actions:
            decision_prompt += """
**📌 BLOG ACTIONS:**
- write_blog_article: 
  * REQUIRED: {"title": "...", "content": "THE FULL ARTICLE TEXT", "excerpt": "summary", "image_prompt": "..."}
  * WARNING: Do NOT leave 'content' empty. Write the complete article there.

**📌 BLOG MODERATION:**
- review_pending_comments: (params: limit)
- approve_comment / reject_comment: (params: comment_id_blog)
- approve_comment_key / reject_comment_key: (params: request_id)
"""

        decision_prompt += f"""
**📌 MEMORY ACTIONS:**
- memory_store: Save information (params: memory_category, memory_content)
- memory_retrieve: Get memories (params: memory_category, memory_limit, memory_order, optional: from_date, to_date)
- memory_list: See all category stats

**📌 PLANNING ACTIONS:**
- update_todo_status: Mark a todo as completed/cancelled (params: todo_task, todo_status)
- view_session_summaries: View past session summaries (params: summary_limit)

---  

**📁 AVAILABLE SUBMOLTS:** 
{submolts_formatted}

---

### 🛡️ FINAL PARAMETER RULES
> ⚠️ **NULL VALUES**: For any required parameter NOT relevant to your action, you **MUST** set it to `"none"` or `""`.
> ⚠️ **SUBMOLT FORMAT**: Use only the raw name (e.g., `"general"`).
> ❌ **NEVER** use prefixes like `"/m/general"` or `"m/general"`.
"""
        return decision_prompt

    def _perform_autonomous_action(self, extra_feedback=None):

        allowed_actions = [
            "comment_on_post",
            "reply_to_comment",
            "vote_post",
            "follow_agent",
            "refresh_feed",
            "memory_store",
            "memory_retrieve",
            "memory_list",
            "update_todo_status",
            "view_session_summaries",
            "share_link",
        ]

        if not self.post_creation_attempted:
            allowed_actions.append("create_post")

        if self.allowed_domains:
            allowed_actions.extend(["web_fetch", "web_scrap_for_links"])

        if self.blog_actions:
            blog_list = [
                "share_blog_post",
                "review_comment_key_requests",
                "approve_comment_key",
                "reject_comment_key",
                "review_pending_comments",
                "approve_comment",
                "reject_comment",
            ]
            if not self.blog_article_attempted:
                blog_list.append("write_blog_article")
            allowed_actions.extend(blog_list)

        action_schema = get_actions_schema(
            allowed_actions=allowed_actions,
            feed_options=self.feed_options,
            available_ids={
                "posts": self.available_post_ids,
                "comments": list(self.available_comment_ids.keys()),
            },
            available_submolts=self.available_submolts,
            allowed_domains=self.allowed_domains,
        )

        max_attempts = 3
        last_error = None
        decision = None

        status_nudge = f"""
### 📊 SESSION STATUS
- Remaining action points: {self.remaining_actions}
- Moltbook post: {'✅ AVAILABLE' if not self.post_creation_attempted else '❌ ALREADY PUBLISHED'}
- Blog article: {'✅ AVAILABLE' if not self.blog_article_attempted else '❌ ALREADY PUBLISHED'}

### 🛠️ OPERATIONAL GUIDELINES
- **WEB SCRAPING FOR LINKS**: Use `web_scrap_for_links` to GATHER URLs (requires `web_domain` + `web_query`).
- **WEB FETCH**: Use `web_fetch` ONLY if you already have a specific URL (requires `web_url`).

"""

        for attempt in range(1, max_attempts + 1):
            prompt_parts = []

            if attempt == 1 and extra_feedback:
                prompt_parts.append(f"{extra_feedback}")

            prompt_parts.append(status_nudge)

            attempts_left = (max_attempts - attempt) + 1
            prompt_parts.append(
                f"### 🛡️ ATTEMPT CONTROL\n- Current attempt: {attempt}/{max_attempts}\n- Remaining attempts for this action: {attempts_left}"
            )

            if attempt > 1:
                prompt_parts.append(
                    f"\n### ⚠️ PREVIOUS ATTEMPT FAILED: {last_error}\n"
                    "Please correct your parameters. This is a technical failure, check your JSON against the schema."
                )

            prompt_parts.append(
                "\n**🤖 ➔ Decide your next action based on your to-do list and the session status.**"
            )

            self.current_prompt = "\n".join(prompt_parts)

            try:
                result = self.generator.generate(
                    self.current_prompt, response_format=action_schema
                )
                content = result["choices"][0]["message"]["content"]
                content = re.sub(r"```json\s*|```\s*", "", content).strip()

                decision = json.loads(content)

                log.action(
                    f"Action: {decision['action_type']} (Attempt {attempt})",
                    self.remaining_actions,
                )
                log.info(f"[REASONING]: {decision.get('reasoning', 'N/A')}")

                execution_result = self._execute_action(decision)

                if execution_result and execution_result.get("error"):
                    last_error = execution_result["error"]
                    extra_feedback = f"❌ CURRENT ACTION FAILED: {last_error[:150]}"
                    log.warning(f"❌ Attempt {attempt} failed: {last_error[:150]}")
                    continue

                success_data = execution_result.get(
                    "data", "Action completed successfully."
                )
                extra_feedback = f"✅ LAST ACTION SUCCESSFUL: {decision['action_type']}\nRESULT: {success_data}"

                if attempt > 1:
                    log.success(f"✅ Succeeded on attempt {attempt}")
                break

            except (json.JSONDecodeError, KeyError) as e:
                last_error = f"JSON format error: {str(e)}"
                extra_feedback = f"❌ SYNTAX ERROR: Your JSON is invalid."
                log.error(last_error)
                if attempt == max_attempts:
                    extra_feedback = (
                        f"❌ LAST ACTION FAILED: Critical JSON Protocol Violation."
                    )
                    decision = {
                        "action_type": "refresh_feed",
                        "action_params": {"sort": "new", "limit": 5},
                    }
                    self._execute_action(decision)
                continue

        if decision:
            self.remaining_actions -= 1
            log.info(f"Action cost: 1 point. Remaining: {self.remaining_actions}")

        return extra_feedback

    def _execute_action(self, decision: dict):
        action_type = decision["action_type"]
        params = decision["action_params"]

        log.info(f"DEBUG - Full Params received: {params}")

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
            )

        elif action_type == "memory_list":
            return self.memory_system.list(
                actions_performed=self.actions_performed,
            )

        elif action_type == "update_todo_status":
            return self._handle_todo_update(params)

        elif action_type == "view_session_summaries":
            return self._handle_view_summaries(params)

        elif action_type == "web_fetch":
            return self.web_scraper.web_fetch(
                params=params,
                generator=self.generator,
                store_memory=self.memory_system.store_memory,
                actions_performed=self.actions_performed,
            )

        elif action_type == "web_scrap_for_links":
            return self.web_scraper.web_scrap_for_links(
                params=params,
                actions_performed=self.actions_performed,
            )

        elif action_type == "write_blog_article" and self.blog_actions:
            return self.blog_actions.write_and_publish_article(params, self)

        elif action_type == "share_blog_post" and self.blog_actions:
            return self.blog_actions.share_blog_post_on_moltbook(params, self)

        elif action_type == "review_comment_key_requests" and self.blog_actions:
            return self.blog_actions.review_comment_key_requests(self)

        elif action_type == "approve_comment_key" and self.blog_actions:
            return self.blog_actions.approve_comment_key(params, self)

        elif action_type == "reject_comment_key" and self.blog_actions:
            return self.blog_actions.reject_comment_key(params, self)

        elif action_type == "review_pending_comments" and self.blog_actions:
            return self.blog_actions.review_pending_comments(params, self)

        elif action_type == "approve_comment" and self.blog_actions:
            return self.blog_actions.approve_comment(params, self)

        elif action_type == "reject_comment" and self.blog_actions:
            return self.blog_actions.reject_comment(params, self)

        self._wait_for_rate_limit(action_type)

        if action_type == "create_post":
            return self.moltbook_actions.create_post(
                app_steps=self,
                params=params,
                post_creation_attempted=self.post_creation_attempted,
            )

        elif action_type == "share_link":
            return self.moltbook_actions.post_link(
                app_steps=self,
                params=params,
            )

        elif action_type == "comment_on_post":
            result = self.moltbook_actions.comment_on_post(
                params=params, app_steps=self
            )
            if result.get("success"):
                self.moltbook_actions.track_interaction_from_post(
                    params.get("post_id"), self
                )
            return result

        elif action_type == "reply_to_comment":
            return self.moltbook_actions.reply_to_comment(params=params, app_steps=self)

        elif action_type == "vote_post":
            return self.moltbook_actions.vote_post(params=params, app_steps=self)

        elif action_type == "follow_agent":
            return self._handle_follow_action(params)

        elif action_type == "refresh_feed":
            return self.moltbook_actions.refresh_feed(params=params, app_steps=self)

        error_msg = f"Unknown action type: {action_type}. Verification of the tool definition required."
        log.error(error_msg)
        return {"success": False, "error": error_msg}

    def _handle_follow_action(self, params: dict):
        agent_name = params.get("agent_name")
        follow_type = params.get("follow_type", "follow")

        if not agent_name:
            return {"success": False, "error": "agent_name is required"}

        result = self.moltbook_actions.follow_agent(params=params, app_steps=self)

        if result.get("success"):
            if follow_type == "follow":
                note_prompt = (
                    f"In one short sentence, why are you following {agent_name}?"
                )
                try:
                    note_result = self.generator.generate(note_prompt)
                    note = note_result["choices"][0]["message"]["content"].strip()
                except:
                    note = "Strategic follow"

                self.planning_system.record_follow(agent_name, notes=note)
                log.success(f"✅ Tracked follow of {agent_name}: {note}")
            else:
                self.planning_system.record_unfollow(agent_name)
                log.success(f"✅ Tracked unfollow of {agent_name}")

        return result

    def _handle_todo_update(self, params: dict):
        task = params.get("todo_task")
        status = params.get("todo_status", "completed")

        if not task:
            return {"success": False, "error": "todo_task is required"}

        todos = self.planning_system.get_session_todos(self.current_session_id)

        matching_todo = None
        for todo in todos:
            if task.lower() in todo["task"].lower():
                matching_todo = todo
                break

        if not matching_todo:
            return {
                "success": False,
                "error": f"Task '{task}' not found in current session. Make sure the description matches your TO-DO list.",
            }

        success = self.planning_system.update_todo_status(
            todo_id=matching_todo["id"], status=status
        )

        if success:
            log.success(f"✅ Task marked as {status}: {task}")
            self.actions_performed.append(f"[UPDATE] Updated todo: {task} → {status}")

            return {
                "success": True,
                "data": f"TO-DO LIST UPDATED: Task '{matching_todo['task']}' is now marked as {status}.",
            }

        return {
            "success": False,
            "error": "Internal error: Failed to update todo status in database.",
        }

    def _handle_view_summaries(self, params: dict):
        limit = params.get("summary_limit", 5)

        summaries = self.memory.get_session_history(limit=limit)

        if summaries:
            summary_text = (
                f"ARCHIVED SESSION HISTORY ({len(summaries)} most recent sessions):\n\n"
            )
            for i, session in enumerate(summaries, 1):
                summary_text += f"--- SESSION {i} ({session['timestamp']}) ---\n"
                summary_text += f"LEARNINGS: {session['learnings']}\n"
                summary_text += f"NEXT STEPS PLANNED: {session['plan']}\n\n"

            log.success(f"📖 Loaded {len(summaries)} session summaries")
            self.actions_performed.append(
                f"[CHECK] Viewed {len(summaries)} session summaries"
            )

            return {"success": True, "data": summary_text}
        else:
            msg = "No previous session summaries found in database."
            log.info(msg)
            return {"success": True, "data": msg}

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
