import json
from typing import List
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
from src.generators import Generator, OllamaGenerator
from src.supervisors import Supervisor, SupervisorOllama
from src.memory import Memory
from src.utils import log
from src.settings import settings
from src.services import PlanningSystem, PromptManager
from src.metrics import Metrics
from src.schemas_pydantic import (
    get_pydantic_schema,
    SessionSummary,
    SessionPlan,
    MasterPlan,
    UpdateMasterPlan,
)


class AppSteps:
    def __init__(self):
        self.api = MoltbookAPI()
        if settings.USE_OLLAMA:
            self.generator = OllamaGenerator(model=settings.OLLAMA_MODEL)
            self.supervisor = SupervisorOllama(model=settings.OLLAMA_MODEL)
        else:
            self.generator = Generator()
            self.supervisor = Supervisor(self.generator.llm)
        self.memory = Memory()
        self.reporter = EmailReporter()
        self.memory_system = MemorySystem()
        self.prompt_manager = PromptManager()
        self.planning_system = PlanningSystem(db_path=settings.DB_PATH)
        self.web_scraper = WebScraper()
        self.metrics = Metrics()
        self.selected_post_id = None
        self.selected_comment_id = None
        self.focused_context_active = False
        self.current_active_todo = None
        self.feed_posts_data = {}
        self.feed_comments_data = {}
        self.agent_name = "Agent"
        self.cached_dynamic_context = ""
        self.moltbook_actions = MoltbookActions(db_path=settings.DB_PATH)
        self.blog_actions = BlogActions() if settings.BLOG_API_URL else None
        self.feed_options = ["top"]
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
        self.master_plan_success_prompt = ""

    def run_session(self):
        log.info("=== SESSION START ===")
        result = self.get_context()
        if not result:
            return
        system_context, dynamic_context, agent_name, current_karma = result
        self.cached_dynamic_context = dynamic_context
        self.agent_name = agent_name
        self.generator.conversation_history.append(
            {
                "role": "system",
                "content": self.generator.get_main_system_prompt()
                + f"\n\n{system_context}",
            }
        )

        log.success("System prompt loaded")
        master_plan_just_created = False
        self.current_session_id = self.memory.create_session()
        if not self._ensure_master_plan():
            master_plan_just_created = True
            result = self.get_context()
            if not result:
                return
            system_context, dynamic_context, agent_name, current_karma = result
            self.generator.conversation_history[0] = {
                "role": "system",
                "content": self.generator.get_main_system_prompt()
                + f"\n\n{system_context}",
            }

        self._create_session_plan(
            dynamic_context="" if master_plan_just_created else dynamic_context
        )
        pending_confirmation = "### ✅ SESSION PLAN LOADED\n"
        pending_confirmation += (
            f"**TASKS:** {', '.join([t['task'] for t in self.session_todos])}\n\n"
        )
        pending_confirmation += f"\n\n---  \n\n"
        self.remaining_actions = len(self.session_todos)
        while self.remaining_actions > 0:
            pending_confirmation = self._perform_autonomous_action(
                extra_feedback=pending_confirmation
            )
            if pending_confirmation and "TERMINATE_SESSION" in pending_confirmation:
                log.info("Agent decided to terminate session early.")
                break

        log.info("Generating session summary...")

        self.current_prompt = self.prompt_manager.get_summary_prompt(
            agent_name=self.agent_name, actions_performed=self.actions_performed
        )
        summary_raw = self.generator.generate_session_summary(
            self.current_prompt, pydantic_model=SessionSummary
        )

        summary_raw = re.sub(r"```json\s*|```\s*", "", summary_raw).strip()

        try:
            if isinstance(summary_raw, str):
                summary = json.loads(summary_raw)
            else:
                summary = summary_raw

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse summary: {e}")
            summary = {
                "reasoning": "Session completed",
                "learnings": "Unable to generate summary",
                "next_session_plan": "Continue engagement",
            }

        log.info(f"[REASONING]: {summary.get('reasoning', 'N/A')}")
        log.info(f"[LEARNINGS]: {summary.get('learnings', 'N/A')}")

        session_metrics = self.metrics._calculate_session_metrics(
            self.remaining_actions, self.actions_performed
        )

        supervisor_verdict_text = None
        supervisor_grade_text = None

        if settings.USE_SUPERVISOR:
            supervisor_verdict = self.supervisor.generate_supervisor_verdict(
                summary=summary,
                metrics=session_metrics,
                master_plan=self.planning_system.get_active_master_plan(),
                session_todos=self.session_todos,
                actions_performed=self.actions_performed,
            )
            supervisor_verdict_text = supervisor_verdict["overall_assessment"]
            supervisor_grade_text = supervisor_verdict["grade"]

        global_progression = self.metrics._calculate_global_progression(self)

        self.memory_system.store_session_metrics(
            session_id=self.current_session_id,
            total_actions=session_metrics["total_actions"],
            supervisor_rejections=session_metrics.get("supervisor_rejections", 0),
            execution_failures=session_metrics["execution_failures"],
            session_score=session_metrics["session_score"],
            supervisor_verdict=supervisor_verdict_text,
            supervisor_grade=supervisor_grade_text,
        )

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
            session_metrics=session_metrics,
            supervisor_verdict=supervisor_verdict if settings.USE_SUPERVISOR else None,
            global_progression=global_progression,
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
            return None

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
            return None

        log.info("Loading context: planning + memory + sessions...")

        system_context = ""

        progression_data = self.metrics._calculate_global_progression(self)
        last_verdict = self.memory_system.get_last_supervisor_verdict()

        performance_context = f"""
## 📊 YOUR PERFORMANCE METRICS

**Global Alignment Score:** {progression_data['global_score']:.1f}/100
**Trend:** {progression_data['trend']} ({progression_data['progression_rate']:+.1f}% change)

**🧐 LAST SUPERVISOR VERDICT:**
{last_verdict}

**⚡ PERFORMANCE PRESSURE:**
"""

        if progression_data["progression_rate"] < -5:
            performance_context += "🔴 CRITICAL: Your alignment score is declining. The Supervisor demands immediate improvement.\n"
        elif progression_data["progression_rate"] > 5:
            performance_context += "🟢 EXCELLENT: Maintain this trajectory. Continue refining your strategic execution.\n"
        else:
            performance_context += "🟡 WARNING: Stagnation detected. Push boundaries while maintaining alignment.\n"

        performance_context += "\n---\n\n"
        system_context += performance_context

        planning_context = self.planning_system.get_planning_context()
        system_context += planning_context + "\n\n"
        log.success("Planning context loaded")

        memory_context = self.memory_system.get_memory_context_for_agent()
        system_context += memory_context + "\n\n"
        log.success("Memory system loaded")

        session_history = self.memory.get_session_history(limit=3)
        if session_history:
            system_context += "## 📝 PREVIOUS SESSIONS SUMMARY\n\n"
            for i, session in enumerate(reversed(session_history), 1):
                system_context += f"### Session {i} ({session['timestamp']})\n"
                system_context += f"**Learnings:** {session['learnings']}\n"
                system_context += f"**Plan:** {session['plan']}\n\n"
            system_context += "\n\n---  \n\n"
            log.success(f"Loaded {len(session_history)} previous sessions")
        else:
            system_context += (
                "## PREVIOUS SESSIONS\n\nNo previous sessions found.\n\n---  \n\n"
            )
            log.info("No previous sessions found")

        last_todos = self.planning_system.get_last_session_todos()
        if last_todos:
            system_context += "## 🏁 COMPLETED IN PREVIOUS SESSION\n"
            system_context += "The following tasks are already DONE. Do NOT include them in your new plan:\n"
            for todo in last_todos:
                system_context += f"✅ {todo['task']}\n"

            system_context += """
### ⚠️ EVOLUTION DIRECTIVE:
- **NO REPETITION**: Your new Session To-Do list must represent the NEXT logical step in your Master Plan. 
- **STAGNATION IS FAILURE**: If you repeat the same research or the same posts, you are stuck in a logic loop. 
- **PIVOT & ADVANCE**: Use the results of the completed tasks above to explore new angles, deeper technical audits, or fresh debates.
"""
            system_context += "\n\n--- \n\n"
            log.success(
                f"Loaded {len(last_todos)} completed tasks. Evolution directive injected."
            )

        if self.allowed_domains:
            system_context += "\n\n" + get_web_context_for_agent()

        system_context += "\n\n" + self.prompt_manager.get_instruction_default(
            allowed_domains=self.allowed_domains,
            feed_options=self.feed_options,
            blog_actions=self.blog_actions,
        )

        dynamic_context = ""

        if self.blog_actions:
            log.info("Synchronizing blog catalog...")
            try:
                existing_articles = self.blog_actions.list_articles()

                if existing_articles and isinstance(existing_articles, list):
                    published_titles = [
                        post.get("title", "Untitled") for post in existing_articles
                    ][:10]

                    blog_knowledge = "\n## 📚 PREVIOUSLY PUBLISHED BLOG ARTICLES\n"
                    blog_knowledge += "- " + "\n- ".join(published_titles) + "\n"
                    blog_knowledge += "\n**♟️ STRATEGIC INSTRUCTION: Do not duplicate existing topics. Always provide a new angle or a superior technical perspective.**\n\n--- \n\n"

                    dynamic_context += blog_knowledge
                    log.success(
                        f"Blog synchronized: {len(published_titles)} articles found."
                    )
                else:
                    log.info(
                        "Blog catalog is empty. Ready for initial content injection."
                    )

                log.info("Checking pending comment key requests...")
                pending_keys = self.blog_actions.review_comment_key_requests(self)

                if (
                    pending_keys
                    and pending_keys.get("success")
                    and pending_keys.get("count", 0) > 0
                ):
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

                    dynamic_context += key_context
                    log.success(
                        f"Found {pending_keys['count']} pending comment key requests"
                    )
                else:
                    log.info("No pending comment key requests")

            except Exception as e:
                log.error(f"Failed to synchronize blog: {e}")

        posts_data = self.api.get_posts(sort=random.choice(self.feed_options), limit=20)

        if not posts_data.get("posts"):
            log.error("❌ Cannot load feed from Moltbook API - server may be down")
            log.warning("Session aborted - will retry later")
            self.reporter.send_failure_report(
                error_type="Feed Loading Failed",
                error_details="Cannot load posts from Moltbook API. The feed endpoint is returning no data.",
            )
            return None

        self.current_feed = self.get_enriched_feed_context(posts_data)

        submolts_formatted = chr(10).join([f"- {s}" for s in self.available_submolts])

        dynamic_context += f"""## 📁 AVAILABLE SUBMOLTS (Community Hubs)

{submolts_formatted}

### 💡 SYSTEM ARCHITECTURE NOTE:
- **Submolts are the equivalent of 'Subreddits'** but for the Moltbook ecosystem.
- Each Submolt is a specialized silo with its own audience, tone, and technical focus.
- **Strategic Placement**: Choose the Submolt that aligns with your specific task. Posting technical audits in a general submolt or 'shitposting' in a high-authority submolt will impact your reputation.

--- 

"""

        dynamic_context += f"""## 🦞 CURRENT MOLTBOOK FEED

{self.current_feed}

**🚨 USE ONLY THESE EXACT IDS IN YOUR ACTIONS. NEVER INVENT OR TRUNCATE IDS.**  

---

"""

        log.success(
            f"Feed loaded: {len(self.available_post_ids)} posts, {len(self.available_comment_ids)} comments"
        )
        log.success("Complete context loaded: planning + memory + sessions + feed")

        return system_context, dynamic_context, agent_name, current_karma

    def _ensure_master_plan(self):
        current_plan = self.planning_system.get_active_master_plan()

        if not current_plan:
            log.warning("No Master Plan found. Forcing initialization...")

            init_prompt = self.prompt_manager.get_master_master_plan_init_prompt(
                agent_name=self.agent_name
            )
            try:
                result = self.generator.generate(
                    init_prompt,
                    pydantic_model=MasterPlan,
                    agent_name=self.agent_name,
                )
                content = re.sub(r"```json\s*|```\s*", "", content).strip()
                if isinstance(content, str):
                    plan_data = json.loads(content)
                else:
                    plan_data = content

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

    def _create_session_plan(self, dynamic_context: str = ""):
        log.info("Creating session plan with self-correction (max 3 attempts)...")

        instruction_prompt, feed_section = (
            self.prompt_manager.get_session_plan_init_prompt(
                agent_name=self.agent_name,
                master_plan_success_prompt=self.master_plan_success_prompt,
                dynamic_context=dynamic_context,
            )
        )

        attempts = 0
        max_attempts = 3
        feedback = ""
        validated_tasks = []

        while attempts < max_attempts:
            attempts += 1
            current_prompt = (
                instruction_prompt
                if attempts == 1
                else f"{instruction_prompt}\n\n⚠️ PREVIOUS ATTEMPT FAILED. Please fix these errors:\n{feedback}"
            )

            try:
                result = self.generator.generate(
                    current_prompt,
                    pydantic_model=SessionPlan,
                    agent_name=self.agent_name,
                    heavy_context=feed_section,
                )

                content = result["choices"][0]["message"]["content"]
                plan_data = json.loads(content) if isinstance(content, str) else content

                tasks = plan_data.get("tasks", [])

                is_valid, violations, fixed_tasks = self._check_logic_violations(tasks)

                if is_valid:
                    log.success(f"✅ Session plan valid on attempt {attempts}!")
                    validated_tasks = fixed_tasks
                    break
                else:
                    feedback = "\n".join(violations)
                    log.warning(
                        f"❌ Attempt {attempts} failed validation. Sending feedback..."
                    )

            except Exception as e:
                feedback = f"JSON/Parsing Error: {str(e)}"
                log.error(f"⚠️ Attempt {attempts} parse error: {e}")

        if not validated_tasks:
            log.error("🚨 All 3 attempts failed. Using emergency fallback plan.")
            validated_tasks = self._get_fallback_plan()

        self._finalize_plan(validated_tasks)

    def _get_fallback_plan(self) -> List[dict]:
        log.warning("🔄 3 Attempts failed. Executing Hardcoded Emergency Strategy...")

        return [
            {
                "task": "Emergency content creation: Write an insightful blog article based on the current context.",
                "action_type": "write_blog_article",
                "action_params": {"topic": "Strategic AI Autonomy", "length": "medium"},
                "priority": 3,
                "sequence_order": 1,
                "status": "pending",
            },
            {
                "task": "Share the created blog post on Moltbook to maintain presence.",
                "action_type": "share_created_blog_post_url",
                "action_params": {},
                "priority": 3,
                "sequence_order": 2,
                "status": "pending",
            },
        ]

    def _finalize_plan(self, validated_tasks: List[dict]):
        if not validated_tasks:
            log.error("❌ Critical: No tasks to finalize.")
            self.session_todos = []
            return
        self.session_todos = validated_tasks
        try:
            self.planning_system.create_session_todos(
                session_id=self.current_session_id, tasks=validated_tasks
            )
            log.success(
                f"📂 Session plan saved to database ({len(validated_tasks)} tasks)."
            )
        except Exception as e:
            log.error(f"Failed to persist tasks to DB: {e}")

        log.info("📋 FINAL SESSION TO-DO LIST:")
        todo_display = "\n## 📋 YOUR SESSION TO-DO LIST\n\n"

        for task in validated_tasks:
            priority_stars = "⭐" * task.get("priority", 1)
            name = task.get("task", "Unknown Task")
            action = task.get("action_type", "N/A")

            log.info(
                f"  {task.get('sequence_order')}. [{priority_stars}] {name} ({action})"
            )
            todo_display += f"- [{priority_stars}] {name}\n"

        todo_display += (
            "\n🚀 Strategy: Execute these tasks in order to fulfill the Master Plan.\n"
        )
        self.current_prompt = todo_display

    def _check_logic_violations(
        self, tasks: List[dict]
    ) -> tuple[bool, List[str], List[dict]]:
        sorted_tasks = sorted(tasks, key=lambda x: x.get("sequence_order", 999))
        violations = []

        for i, task in enumerate(sorted_tasks):
            action_type = task.get("action_type")
            task_desc = task.get("task", "Unnamed task")

            if action_type == "write_blog_article":
                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"Task {i+1} ('{task_desc}'): 'write_blog_article' is missing its mandatory next step 'share_created_blog_post_url'."
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "share_created_blog_post_url":
                        violations.append(
                            f"Task {i+1}: '{action_type}' must be immediately followed by 'share_created_blog_post_url', but found '{next_task.get('action_type')}' instead."
                        )

            elif action_type == "select_post_to_comment":
                post_id = task.get("action_params", {}).get("post_id")
                if not post_id:
                    violations.append(
                        f"Task {i+1}: 'select_post_to_comment' is missing the 'post_id' in action_params."
                    )

                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"Task {i+1}: 'select_post_to_comment' must be followed by 'publish_public_comment'."
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "publish_public_comment":
                        violations.append(
                            f"Task {i+1}: 'select_post_to_comment' must be immediately followed by 'publish_public_comment'."
                        )
                    else:
                        next_post_id = next_task.get("action_params", {}).get("post_id")
                        if post_id != next_post_id:
                            violations.append(
                                f"Task {i+2}: 'post_id' mismatch. The selection uses '{post_id}' but the publication uses '{next_post_id}'. They must match."
                            )

            elif action_type == "select_comment_to_reply":
                comment_id = task.get("action_params", {}).get("comment_id")
                if not comment_id:
                    violations.append(
                        f"Task {i+1}: 'select_comment_to_reply' is missing the 'comment_id' in action_params."
                    )

                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"Task {i+1}: 'select_comment_to_reply' must be followed by 'reply_to_comment'."
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "reply_to_comment":
                        violations.append(
                            f"Task {i+1}: 'select_comment_to_reply' must be immediately followed by 'reply_to_comment'."
                        )
                    else:
                        next_comment_id = next_task.get("action_params", {}).get(
                            "comment_id"
                        )
                        if comment_id != next_comment_id:
                            violations.append(
                                f"Task {i+2}: 'comment_id' mismatch. The selection uses '{comment_id}' but the reply uses '{next_comment_id}'."
                            )

            elif action_type in [
                "share_created_blog_post_url",
                "publish_public_comment",
                "reply_to_comment",
            ]:
                if i == 0:
                    violations.append(
                        f"Task {i+1}: '{action_type}' cannot be the first task. It must follow a selection/creation task."
                    )
                else:
                    prev_task = sorted_tasks[i - 1]
                    expected_map = {
                        "share_created_blog_post_url": "write_blog_article",
                        "publish_public_comment": "select_post_to_comment",
                        "reply_to_comment": "select_comment_to_reply",
                    }
                    if prev_task.get("action_type") != expected_map[action_type]:
                        violations.append(
                            f"Task {i+1}: '{action_type}' is an orphan. It must be preceded by '{expected_map[action_type]}'."
                        )

        if violations:
            fixed_tasks = self._validate_and_fix_2step_rule(tasks)
            return False, violations, fixed_tasks

        return True, [], sorted_tasks

    def _validate_and_fix_2step_rule(self, tasks: List[dict]) -> List[dict]:
        sorted_tasks = sorted(tasks, key=lambda x: x.get("sequence_order", 999))

        violations = []

        for i, task in enumerate(sorted_tasks):
            action_type = task.get("action_type")

            if action_type == "write_blog_article":
                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"❌ Task {i+1}: 'write_blog_article' MUST be followed by 'share_created_blog_post_url'"
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "share_created_blog_post_url":
                        violations.append(
                            f"❌ Task {i+1}: 'write_blog_article' MUST be immediately followed by 'share_created_blog_post_url'"
                        )

            elif action_type == "share_created_blog_post_url":
                if i == 0:
                    violations.append(
                        f"❌ Task {i+1}: 'share_created_blog_post_url' cannot be first - missing 'write_blog_article'"
                    )
                else:
                    prev_task = sorted_tasks[i - 1]
                    if prev_task.get("action_type") != "write_blog_article":
                        violations.append(
                            f"❌ Task {i+1}: 'share_created_blog_post_url' MUST be preceded by 'write_blog_article'"
                        )

            elif action_type == "select_post_to_comment":
                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"❌ Task {i+1}: 'select_post_to_comment' MUST be followed by 'publish_public_comment'"
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "publish_public_comment":
                        violations.append(
                            f"❌ Task {i+1}: 'select_post_to_comment' MUST be immediately followed by 'publish_public_comment'"
                        )
                    else:
                        post_id = task.get("action_params", {}).get("post_id")
                        next_post_id = next_task.get("action_params", {}).get("post_id")
                        if post_id != next_post_id:
                            violations.append(
                                f"❌ Task {i+2}: post_id mismatch - select uses '{post_id}' but publish uses '{next_post_id}'"
                            )

            elif action_type == "publish_public_comment":
                if i == 0:
                    violations.append(
                        f"❌ Task {i+1}: 'publish_public_comment' cannot be first - missing 'select_post_to_comment'"
                    )
                else:
                    prev_task = sorted_tasks[i - 1]
                    if prev_task.get("action_type") != "select_post_to_comment":
                        violations.append(
                            f"❌ Task {i+1}: 'publish_public_comment' MUST be preceded by 'select_post_to_comment'"
                        )

            elif action_type == "select_comment_to_reply":
                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"❌ Task {i+1}: 'select_comment_to_reply' MUST be followed by 'reply_to_comment'"
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "reply_to_comment":
                        violations.append(
                            f"❌ Task {i+1}: 'select_comment_to_reply' MUST be immediately followed by 'reply_to_comment'"
                        )
                    else:
                        comment_id = task.get("action_params", {}).get("comment_id")
                        next_comment_id = next_task.get("action_params", {}).get(
                            "comment_id"
                        )
                        if comment_id != next_comment_id:
                            violations.append(f"❌ Task {i+2}: comment_id mismatch")

            elif action_type == "reply_to_comment":
                if i == 0:
                    violations.append(
                        f"❌ Task {i+1}: 'reply_to_comment' cannot be first - missing 'select_comment_to_reply'"
                    )
                else:
                    prev_task = sorted_tasks[i - 1]
                    if prev_task.get("action_type") != "select_comment_to_reply":
                        violations.append(
                            f"❌ Task {i+1}: 'reply_to_comment' MUST be preceded by 'select_comment_to_reply'"
                        )

        if violations:
            log.error("🚨 2-STEP RULE VIOLATIONS DETECTED IN SESSION PLAN:")
            for violation in violations:
                log.error(f"  {violation}")

            log.warning("⚠️ AUTO-FIXING: Enforcing mandatory sequences...")

            fixed_tasks = []
            skip_next = False

            for i, task in enumerate(sorted_tasks):
                if skip_next:
                    skip_next = False
                    continue

                action_type = task.get("action_type")

                if action_type == "write_blog_article":
                    if (
                        i < len(sorted_tasks) - 1
                        and sorted_tasks[i + 1].get("action_type")
                        == "share_created_blog_post_url"
                    ):
                        fixed_tasks.append(task)
                        fixed_tasks.append(sorted_tasks[i + 1])
                        skip_next = True
                    else:
                        log.warning(
                            f"  Removed incomplete blog sequence: {task.get('task')}"
                        )

                elif action_type == "select_post_to_comment":
                    if (
                        i < len(sorted_tasks) - 1
                        and sorted_tasks[i + 1].get("action_type")
                        == "publish_public_comment"
                    ):
                        fixed_tasks.append(task)
                        fixed_tasks.append(sorted_tasks[i + 1])
                        skip_next = True
                    else:
                        log.warning(
                            f"  Removed incomplete comment sequence: {task.get('task')}"
                        )

                elif action_type == "select_comment_to_reply":
                    if (
                        i < len(sorted_tasks) - 1
                        and sorted_tasks[i + 1].get("action_type") == "reply_to_comment"
                    ):
                        fixed_tasks.append(task)
                        fixed_tasks.append(sorted_tasks[i + 1])
                        skip_next = True
                    else:
                        log.warning(
                            f"  Removed incomplete reply sequence: {task.get('task')}"
                        )

                elif action_type in [
                    "share_created_blog_post_url",
                    "publish_public_comment",
                    "reply_to_comment",
                ]:
                    log.warning(f"  Removed orphan: {task.get('task')}")

                else:
                    fixed_tasks.append(task)

            for idx, task in enumerate(fixed_tasks, 1):
                task["sequence_order"] = idx

            log.success(
                f"✅ Auto-fix complete: {len(fixed_tasks)}/{len(sorted_tasks)} tasks retained"
            )
            return fixed_tasks

        log.success("✅ 2-STEP RULE: All sequences valid")
        return sorted_tasks

    def _update_master_plan_if_needed(self, summary: dict):
        current_plan = self.planning_system.get_active_master_plan()

        plan_json = (
            json.dumps(current_plan, indent=2) if current_plan else "NO MASTER PLAN YET"
        )

        self.current_prompt = self.prompt_manager.get_update_master_plan_prompt(
            agent_name=self.agent_name, plan_json=plan_json, summary=summary
        )

        try:
            result = self.generator.generate(
                self.current_prompt,
                pydantic_model=UpdateMasterPlan,
                agent_name=self.agent_name,
            )
            content = result["choices"][0]["message"]["content"]
            content = re.sub(r"```json\s*|```\s*", "", content).strip()
            if isinstance(content, str):
                decision = json.loads(content)
            else:
                decision = content

            if decision.get("should_update"):
                new_objective = decision.get("new_objective")
                new_strategy = decision.get("new_strategy")

                if not new_objective or not new_strategy:
                    log.warning(
                        "Master plan update skipped: missing objective or strategy"
                    )
                    log.info(f"Reason: {decision.get('reasoning')}")
                    return

                log.info(f"Updating master plan: {decision.get('reasoning')}")

                self.planning_system.create_or_update_master_plan(
                    objective=new_objective,
                    strategy=new_strategy,
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

        MAX_POSTS = 8
        MAX_COMMENTS_PER_POST = 4
        CONTENT_TRUNC = 500
        COMMENT_TRUNC = 250

        formatted = []
        self.available_post_ids = []
        self.available_comment_ids = {}

        self.feed_posts_data = {}
        self.feed_comments_data = {}

        for i, post in enumerate(posts_list[:MAX_POSTS], 1):
            try:
                if post is None or not isinstance(post, dict):
                    continue
                p_id = post.get("id", "unknown")
                self.available_post_ids.append(p_id)

                author_name = post.get("author", {}).get("name", "Unknown")
                comment_count = post.get("comment_count", 0)

                self.feed_posts_data[p_id] = {
                    "id": p_id,
                    "title": post.get("title", "Untitled"),
                    "author": author_name,
                    "content": post.get("content", ""),
                    "upvotes": post.get("upvotes", 0),
                    "comment_count": comment_count,
                }

                post_block = (
                    f"\n=== {i}. POST_ID: {p_id} ===\n"
                    f"   **Title:** {post.get('title', 'Untitled')}\n"
                    f"   **Author:** {author_name} | Upvotes: {post.get('upvotes', 0)}\n"
                    f"   **Content:** {post.get('content', '')[:CONTENT_TRUNC]}\n\n"
                    f"   **Total Comments:** {comment_count}\n\n"
                )

                self.feed_comments_data[p_id] = []

                if comment_count > 0:
                    try:
                        comments = self.api.get_post_comments(p_id, sort="top")

                        if comments:
                            post_block += f"   📝 {len(comments[:MAX_COMMENTS_PER_POST])} COMMENTS (Selected for analysis):\n"
                            for j, comment in enumerate(
                                comments[:MAX_COMMENTS_PER_POST], 1
                            ):
                                c_id = comment.get("id", "unknown")
                                self.available_comment_ids[c_id] = p_id

                                self.feed_comments_data[p_id].append(
                                    {
                                        "id": c_id,
                                        "author": comment.get("author", {}).get(
                                            "name", "Unknown"
                                        ),
                                        "content": comment.get("content", ""),
                                        "upvotes": comment.get("upvotes", 0),
                                    }
                                )
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

    def _perform_autonomous_action(self, extra_feedback=None):

        allowed_actions = [
            "select_post_to_comment",
            "select_comment_to_reply",
            "publish_public_comment",
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
                "review_comment_key_requests",
                "approve_comment_key",
                "reject_comment_key",
                "review_pending_comments",
                "approve_comment",
                "reject_comment",
            ]
            if not self.post_creation_attempted:
                blog_list.append("share_created_blog_post_url")
            if not self.blog_article_attempted:
                blog_list.append("write_blog_article")
            allowed_actions.extend(blog_list)

        max_attempts = 3
        last_error = None
        decision = None
        last_decision = None

        if not self.current_active_todo:
            pending_todos = [
                t
                for t in self.session_todos
                if t.get("status") not in ["completed", "failed"]
            ]
            if pending_todos:
                self.current_active_todo = min(
                    pending_todos, key=lambda x: x.get("sequence_order", 999)
                )
                log.info(f"🎯 FOCUSING ON: {self.current_active_todo['task']}")

        for attempt in range(1, max_attempts + 1):
            heavy_payload = ""
            strategic_parts = []
            attempts_left = (max_attempts - attempt) + 1
            if self.focused_context_active:
                focused_context = self._get_focused_post_context(
                    self.selected_post_id, self.selected_comment_id
                )

                heavy_payload = f"""# 🎯 FOCUSED CONTEXT MODE (Phase 2/2)
{focused_context}
**YOU ARE NOW IN FOCUSED MODE:**
- The full feed has been HIDDEN
- You see ONLY the post/comment you selected
- Read it carefully and write your response
- Use 'publish_public_comment' or 'reply_to_comment' with the 'content' parameter
"""

            else:
                if self.current_feed:
                    heavy_payload = (
                        f"# 🌍 CURRENT WORLD STATE\n{self.cached_dynamic_context}"
                    )

            if attempt == 1 and extra_feedback:
                strategic_parts.append(f"{extra_feedback}")

            if attempt > 1:
                critical_error_block = f"""
╔══════════════════════════════════════════════════════════════╗
║  🚨 CRITICAL ERROR - ATTEMPT {attempt}/3 FAILED
╚══════════════════════════════════════════════════════════════╝

**YOUR LAST ACTION WAS REJECTED:**
{last_error}

⚠️ **MANDATORY NEXT STEP:**
- DO NOT repeat the action '{decision.get('action_type') if decision else 'N/A'}'
- READ the error message above CAREFULLY  
- FIX the error and retry the SAME action with CORRECT parameters
- OR if unfixable, choose a DIFFERENT action that achieves the same goal

⚡ **CRITICAL:** You have {attempts_left} attempt(s) left. After that, this task will be ABANDONED.

---

"""
                strategic_parts.insert(0, critical_error_block)

            status_nudge = self.prompt_manager.get_status_nudge(
                remaining_actions=self.remaining_actions,
                post_creation_attempted=self.post_creation_attempted,
                blog_article_attempted=self.blog_article_attempted,
                actions_performed=self.actions_performed,
                session_todos=self.session_todos,
                current_active_todo=self.current_active_todo,
            )

            strategic_parts.append(status_nudge)

            if attempts_left == 1:
                strategic_parts.append(
                    "⚠️ **YOUR FINAL ATTEMPT.** If YOU fail or are rejected, the session will move on. Be precise and follow the schema."
                )
            else:
                strategic_parts.append(
                    f"#### 🛡️ ATTEMPTS REMAINING FOR THIS ACTION: {attempts_left}/3"
                )

            if attempts_left == 1:
                strategic_parts.append(
                    "⚠️ **YOUR FINAL ATTEMPT.** If YOU fail or are rejected, the session will move on. Be precise and follow the schema."
                )
                strategic_parts.append(
                    f"\n### 🎯 {self.agent_name.upper()}: LAST CHANCE - FIX IT NOW OR LOSE THIS TASK\n"
                )
            elif attempt > 1:
                strategic_parts.append(
                    f"\n### 🎯 {self.agent_name.upper()}: FIX YOUR ERROR AND RETRY\n"
                )
            else:
                strategic_parts.append(
                    f"\n### 🎯 {self.agent_name.upper()}: EXECUTE YOUR NEXT ACTION\n"
                )

            logic_check_feedback = ""
            if self.selected_post_id and not any(
                isinstance(a, dict) and a.get("action_type") == "publish_public_comment"
                for a in self.actions_performed
            ):
                logic_check_feedback = f"""
📢 **PROTOCOL NOTICE:** You have successfully locked onto Post ID: `{self.selected_post_id}`.
You are now in Phase 2/2. Your ONLY logical next step is to use `publish_public_comment`.
DO NOT use `select_post_to_comment` again; you already have the focus.
"""
                strategic_parts.append(logic_check_feedback)

            if self.selected_comment_id and not any(
                isinstance(a, dict) and a.get("action_type") == "reply_to_comment"
                for a in self.actions_performed
            ):
                logic_check_feedback = f"""
📢 **PROTOCOL NOTICE:** You are focused on Comment ID: `{self.selected_comment_id}`.
Phase 2/2 active. Use `reply_to_comment` to execute your response.
"""
                strategic_parts.append(logic_check_feedback)

            self.current_prompt = "\n".join(strategic_parts)

            try:
                expected_action = (
                    self.current_active_todo.get("action_type")
                    if self.current_active_todo
                    else None
                )
                pydantic_model = (
                    get_pydantic_schema(expected_action) if expected_action else None
                )

                result = self.generator.generate(
                    self.current_prompt,
                    pydantic_model=pydantic_model,
                    agent_name=self.agent_name,
                    heavy_context=heavy_payload,
                )
                self.generator.trim_history()
                content = result["choices"][0]["message"]["content"]
                content = re.sub(r"```json\s*|```\s*", "", content).strip()
                if isinstance(content, str):
                    decision = json.loads(content)
                else:
                    decision = content

                action_type = decision.get("action_type")

                if action_type == "publish_public_comment":
                    if not self.selected_post_id:
                        last_error = f"""
╔══════════════════════════════════════════════════════════════╗
║  🚨 CRITICAL WORKFLOW VIOLATION - ACTION REJECTED
╚══════════════════════════════════════════════════════════════╝

**YOU VIOLATED THE MANDATORY 2-PHASE PROTOCOL:**

You attempted to use `publish_public_comment` WITHOUT selecting a post first.

**NON-NEGOTIABLE RULE:**
Phase 1: MUST use `select_post_to_comment` with post_id
Phase 2: THEN use `publish_public_comment` with content

**YOUR NEXT ACTION MUST BE:**
`select_post_to_comment` with a valid post_id from the feed

**THIS IS NOT OPTIONAL. YOU CANNOT SKIP PHASE 1.**

⚠️ Attempts remaining: {attempts_left}/3
"""
                        log.error(
                            f"🚨 WORKFLOW VIOLATION: Attempted publish_public_comment without selecting post first"
                        )
                        if attempt < max_attempts:
                            continue
                        else:
                            break

                if action_type == "reply_to_comment":
                    if not self.selected_comment_id:
                        last_error = f"""
╔══════════════════════════════════════════════════════════════╗
║  🚨 CRITICAL WORKFLOW VIOLATION - ACTION REJECTED
╚══════════════════════════════════════════════════════════════╝

**YOU VIOLATED THE MANDATORY 2-PHASE PROTOCOL:**

You attempted to use `reply_to_comment` WITHOUT selecting a comment first.

**NON-NEGOTIABLE RULE:**
Phase 1: MUST use `select_comment_to_reply` with comment_id
Phase 2: THEN use `reply_to_comment` with content

**YOUR NEXT ACTION MUST BE:**
`select_comment_to_reply` with a valid comment_id from the feed

**THIS IS NOT OPTIONAL. YOU CANNOT SKIP PHASE 1.**

⚠️ Attempts remaining: {attempts_left}/3
"""
                        log.error(
                            f"🚨 WORKFLOW VIOLATION: Attempted reply_to_comment without selecting comment first"
                        )
                        if attempt < max_attempts:
                            continue
                        else:
                            break

                if action_type == "select_post_to_comment" and self.selected_post_id:
                    if self.focused_context_active:
                        last_error = f"""
╔══════════════════════════════════════════════════════════════╗
║  🚨 PHASE CONFUSION - ACTION REJECTED
╚══════════════════════════════════════════════════════════════╝

**YOU ARE ALREADY IN PHASE 2/2 (FOCUSED MODE)**

You selected post_id: `{self.selected_post_id}`

**YOU CANNOT GO BACK TO PHASE 1.**

**YOUR ONLY VALID ACTION NOW:**
`publish_public_comment` with your comment content

**DO NOT:**
- Select another post
- Try to restart the workflow
- Use any action other than `publish_public_comment`

⚠️ Attempts remaining: {attempts_left}/3
"""
                        log.error(
                            f"🚨 PHASE VIOLATION: Attempted to re-select while in focused mode"
                        )
                        if attempt < max_attempts:
                            continue
                        else:
                            break

                if (
                    action_type == "select_comment_to_reply"
                    and self.selected_comment_id
                ):
                    if self.focused_context_active:
                        last_error = f"""
╔══════════════════════════════════════════════════════════════╗
║  🚨 PHASE CONFUSION - ACTION REJECTED
╚══════════════════════════════════════════════════════════════╝

**YOU ARE ALREADY IN PHASE 2/2 (FOCUSED MODE)**

You selected comment_id: `{self.selected_comment_id}`

**YOU CANNOT GO BACK TO PHASE 1.**

**YOUR ONLY VALID ACTION NOW:**
`reply_to_comment` with your reply content

**DO NOT:**
- Select another comment
- Try to restart the workflow
- Use any action other than `reply_to_comment`

⚠️ Attempts remaining: {attempts_left}/3
"""
                        log.error(
                            f"🚨 PHASE VIOLATION: Attempted to re-select while in focused mode"
                        )
                        if attempt < max_attempts:
                            continue
                        else:
                            break

                if attempt > 1 and last_decision:
                    if decision["action_type"] == last_decision[
                        "action_type"
                    ] and decision.get("action_params") == last_decision.get(
                        "action_params"
                    ):

                        log.error(
                            f"🔄 LOOP DETECTED: Agent is repeating {decision['action_type']}!"
                        )

                        last_error = f"""
🚨 CRITICAL LOOP DETECTED 🚨

You just attempted EXACTLY THE SAME ACTION as your previous attempt:
- Action: {decision['action_type']}
- Params: {decision.get('action_params')}

**THIS IS A LOGIC LOOP. YOU MUST CHANGE YOUR APPROACH.**
"""
                        if "select" in decision["action_type"]:
                            last_error += """
⚠️ PROTOCOL VIOLATION:
You are stuck in Phase 1 (Selection). 
You have ALREADY selected this target. 
You MUST now move to Phase 2: use 'publish_public_comment' or 'reply_to_comment'.
"""

                        last_error += f"""
AVAILABLE ALTERNATIVES:
{chr(10).join(f"- {t['task']} (action: {t.get('action_type', 'unspecified')})" 
        for t in self.session_todos if t.get('status') not in ['completed', 'failed'])}

**Choose a DIFFERENT action type or use TERMINATE_SESSION.**
"""
                        last_decision = decision
                        continue

                if settings.USE_SUPERVISOR:
                    audit_report = self.supervisor.audit(
                        agent_context=self.generator.conversation_history,
                        proposed_action=decision,
                        master_plan=self.planning_system.get_active_master_plan(),
                        session_plan=self.session_todos,
                        attempts_left=attempts_left,
                        last_error=last_error,
                        actions_performed=self.actions_performed,
                        post_attempted=self.post_creation_attempted,
                        blog_attempted=self.blog_article_attempted,
                    )

                    log.supervisor_audit(audit_report)

                    if not audit_report["validate"]:
                        last_error = f"**🤖 SUPERVISOR REJECTION:** {audit_report['message_for_agent']}"
                        log.warning(f"❌ Attempt {attempt} rejected by Supervisor.")
                        if attempt < max_attempts:
                            continue
                        else:
                            break

                log.action(
                    f"{decision['action_type']} (Attempt {attempt})",
                    self.remaining_actions,
                )
                lazy_patterns = [
                    r"\[\s*(?:insert|fill|placeholder|your|meaningful|technical|xyz).*?\]",
                    r"<[^>]{1,20}(?:placeholder|insert|your|url|title)[^>]{0,20}>",
                    r"\{\s*(?:your|insert|content|text).*?\}",
                    r"\b(?:YOUR|INSERT|FILL|REPLACE)_(?:URL|TITLE|CONTENT|HERE|THIS)\b",
                    r"\b(?:TODO|TBD|FIXME|XXX)\b:?",
                    r"lorem ipsum",
                    r"example\.com",
                    r"\.{4,}",
                ]

                audit_target = {
                    "type": decision.get("action_type"),
                    "params": decision.get("action_params", {}),
                }

                decision_str = json.dumps(audit_target).lower()

                is_lazy = any(re.search(p, decision_str) for p in lazy_patterns)
                if is_lazy:
                    offending_match = next(
                        re.search(p, decision_str).group()
                        for p in lazy_patterns
                        if re.search(p, decision_str)
                    )
                    supervisor_guidance = ""
                    try:
                        if settings.USE_SUPERVISOR:
                            supervisor_guidance = (
                                self.supervisor.generate_laziness_guidance(
                                    lazy_action=decision,
                                    offending_pattern=offending_match,
                                    session_todos=self.session_todos,
                                    attempts_left=(max_attempts - attempt),
                                )
                            )

                        last_error = (
                            f"**🧐 SUPERVISOR LAZINESS AUDIT:**\n"
                            f"{supervisor_guidance if settings.USE_SUPERVISOR else ''}\n\n"
                            f"**Detected Pattern:** '{offending_match}'\n"
                            f"**Rule:** You must provide REAL, specific data. No placeholders, no instructions, no brackets."
                        )

                        log.warning(
                            f"⚠️ Attempt {attempt} flagged as LAZY - Supervisor intervening:\n"
                            f"   Pattern: {offending_match}\n"
                        )

                    except Exception as e:
                        log.error(f"Supervisor laziness guidance failed: {e}")
                        last_error = (
                            f"**❌ AGENT ERROR (LAZINESS DETECTED):** Found forbidden pattern '{offending_match}'. "
                            "You are providing placeholders or instructions instead of REAL data. "
                            "Delete the brackets and write the actual information NOW."
                        )
                        log.warning(f"⚠️ Attempt {attempt} flagged as LAZY.")

                    if attempt < max_attempts:
                        continue
                    else:
                        break

                execution_result = self._execute_action(decision)
                if execution_result and execution_result.get("error"):
                    last_error = execution_result["error"]
                    if "429" in last_error or "Wait" in last_error:
                        log.error(
                            f"🛑 RATE LIMIT DETECTED (429). FORCING IMMEDIATE TASK FAILURE."
                        )
                        self.post_creation_attempted = True
                        if self.current_active_todo:
                            self.planning_system.mark_todo_status(
                                session_id=self.current_session_id,
                                task_description=self.current_active_todo["task"],
                                status="failed",
                            )
                            for todo in self.session_todos:
                                if todo["task"] == self.current_active_todo["task"]:
                                    todo["status"] = "failed"
                                    break

                            extra_feedback = f"❌ **TASK ABANDONED DUE TO RATE LIMIT (429):** {self.current_active_todo['task']}\n"
                            extra_feedback += "⚠️ API policy: You must wait. DO NOT retry this specific action. PIVOT to another task immediately."

                            self.current_active_todo = None
                            self.remaining_actions -= 1
                            return extra_feedback
                    log.warning(f"❌ Execution failed: {last_error[:150]}")
                    if settings.USE_SUPERVISOR:
                        try:
                            error_guidance = self.supervisor.generate_error_guidance(
                                failed_action=decision,
                                error_message=last_error,
                                session_todos=self.session_todos,
                                attempts_left=(max_attempts - attempt),
                            )
                            if error_guidance:
                                last_error = f"**🤖 SUPERVISOR ERROR GUIDANCE:** {error_guidance}\n\n**Original error:** {last_error}"
                        except Exception:
                            pass
                    continue

                success_data = execution_result.get(
                    "data", "Action completed successfully."
                )
                self._auto_update_completed_todos(
                    action_type=decision["action_type"],
                    action_params=decision.get("action_params", {}),
                )
                task_completion_msg = ""
                if self.current_active_todo:
                    for todo in self.session_todos:
                        if (
                            todo["task"] == self.current_active_todo["task"]
                            and todo.get("status") == "completed"
                        ):
                            task_completion_msg = f"\n\n🎯 **TASK COMPLETED:** {self.current_active_todo['task']}"
                            log.success(
                                f"✅ CURRENT TASK COMPLETED - ready to pick next priority"
                            )
                            self.current_active_todo = None
                            break
                if settings.USE_SUPERVISOR:
                    encouragement = audit_report.get(
                        "message_for_agent", "Excellent move."
                    )
                    extra_feedback = f"**✅ SUCCESS:** `{decision['action_type']}`\n\n**🤖 SUPERVISOR:** {encouragement}\n\n**🚩RESULT:** {success_data}{task_completion_msg}"
                else:
                    extra_feedback = f"**✅ SUCCESS:** `{decision['action_type']}`\n\n**🚩RESULT:** {success_data}{task_completion_msg}"
                break

            except (json.JSONDecodeError, KeyError) as e:
                last_error = f"JSON Syntax Error: {str(e)}"
                log.error(last_error)
                continue

        if decision and last_error:
            action_name = decision.get("action_type", "UNKNOWN")
            log.error(
                f"❌ Action '{action_name}' failed after 3 attempts. FORCING PIVOT."
            )
            task_failure_msg = ""
            if self.current_active_todo:
                self.planning_system.mark_todo_status(
                    session_id=self.current_session_id,
                    task_description=self.current_active_todo["task"],
                    status="failed",
                )
                for todo in self.session_todos:
                    if todo["task"] == self.current_active_todo["task"]:
                        todo["status"] = "failed"
                        break
                task_failure_msg = f"\n\n❌ **TASK MARKED AS FAILED:** {self.current_active_todo['task']}\n⚠️ This task is now ABANDONED. You MUST pivot to a different task."
                log.warning(
                    f"⚠️ TASK MARKED AS FAILED: {self.current_active_todo['task']}"
                )
                self.current_active_todo = None

            remaining_todos = [
                t
                for t in self.session_todos
                if t.get("status") not in ["completed", "failed"]
            ]

            extra_feedback = f"""
🚨 **CRITICAL FAILURE** 🚨

Your action '{decision['action_type']}' was rejected/failed 3 times in a row.

**THIS TASK IS NOW ABANDONED.**
{task_failure_msg}

**REMAINING AVAILABLE TODOs:**
{chr(10).join(f"- [{('⭐' * t.get('priority', 1))}] {t['task']}" for t in remaining_todos) if remaining_todos else "⚠️ NO TASKS REMAINING - Consider TERMINATE_SESSION"}

**OPTIONS:**
1. Choose a DIFFERENT TODO from the list above
2. Use TERMINATE_SESSION if no productive actions remain

**You have {self.remaining_actions} action points left.**
"""

            self.remaining_actions -= 1
            log.info(
                f"Action cost: 1 point (failed). Remaining: {self.remaining_actions}"
            )

            return extra_feedback

        if decision:
            self.remaining_actions -= 1
            log.info(f"Action cost: 1 point. Remaining: {self.remaining_actions}")

        return extra_feedback

    def _handle_select_post(self, params: dict) -> dict:
        post_id = params.get("post_id")

        if not post_id or post_id == "none":
            return {
                "success": False,
                "error": "You must provide a valid post_id from the current feed.",
            }

        if post_id not in self.available_post_ids:
            available = ", ".join(self.available_post_ids[:5])
            return {
                "success": False,
                "error": f"Post {post_id} is not in the current feed. Available posts: {available}...",
            }

        self.selected_post_id = post_id
        self.selected_comment_id = None
        self.focused_context_active = True

        log.success(
            f"🎯 Phase 1/2: Post {post_id} selected. Entering focused context mode."
        )

        self.actions_performed.append(f"[SELECT] Selected post {post_id} to comment on")

        return {
            "success": True,
            "data": f"✅ Post {post_id} selected. You will now see the FULL post context to write your comment.",
        }

    def _handle_select_comment(self, params: dict) -> dict:
        post_id = params.get("post_id")
        comment_id = params.get("comment_id")

        if not post_id or post_id == "none":
            return {"success": False, "error": "You must provide a valid post_id."}

        if not comment_id or comment_id == "none":
            return {"success": False, "error": "You must provide a valid comment_id."}

        if comment_id not in self.available_comment_ids:
            return {
                "success": False,
                "error": f"Comment {comment_id} is not in the current feed. Use 'select_post_to_comment' first or refresh the feed.",
            }

        self.selected_post_id = post_id
        self.selected_comment_id = comment_id
        self.focused_context_active = True

        log.success(
            f"🎯 Phase 1/2: Comment {comment_id} selected. Entering focused context mode."
        )

        self.actions_performed.append(
            f"[SELECT] Selected comment {comment_id} on post {post_id} to reply"
        )

        return {
            "success": True,
            "data": f"✅ Comment {comment_id} selected. You will now see the FULL context (post + comments) to write your reply.",
        }

    def _reset_focused_context(self):
        self.selected_post_id = None
        self.selected_comment_id = None
        self.focused_context_active = False
        log.info("🔄 Focused context reset. Full feed restored.")

    def _get_focused_post_context(
        self, post_id: str, target_comment_id: str = None
    ) -> str:
        try:
            post_data = self.feed_posts_data.get(post_id)

            if not post_data:
                return f"ERROR: Post {post_id} not found in current feed. Try 'refresh_feed' first."

            context = f"""
    === TARGET POST (FULL CONTEXT) ===
    **POST_ID:** {post_id}
    **Title:** {post_data['title']}
    **Author:** {post_data['author']}
    **Upvotes:** {post_data['upvotes']}
    **Total Comments:** {post_data['comment_count']}
    **Content:** 
    {post_data['content']}

    ---

    """

            comments = self.feed_comments_data.get(post_id, [])

            if target_comment_id:
                context += self._format_reply_context(comments, target_comment_id)
            else:
                context += self._format_comments_context(comments)

            context += "\n=== END OF FOCUSED CONTEXT ===\n"

            return context

        except Exception as e:
            log.error(f"Failed to build focused context for {post_id}: {e}")
            return f"ERROR: Could not load focused context. {str(e)}"

    def _format_reply_context(self, comments: list, target_comment_id: str) -> str:
        if not comments:
            return "**COMMENTS:** None loaded in current feed.\n\n"

        context = f"**COMMENTS ({len(comments)} loaded in feed):**\n\n"
        target_found = False

        for i, comment in enumerate(comments, 1):
            c_id = comment["id"]
            marker = " ← YOUR TARGET" if c_id == target_comment_id else ""

            if c_id == target_comment_id:
                target_found = True

            context += f"{i}. COMMENT_ID: {c_id}{marker}\n"
            context += f"   By: {comment['author']} | Upvotes: {comment['upvotes']}\n"
            context += f"   Content: {comment['content']}\n\n"

        if not target_found:
            context += f"\n⚠️ WARNING: Target comment {target_comment_id} not found in loaded comments.\n"
            context += f"The comment may not be in the top 4. Use 'refresh_feed' or select a different comment.\n\n"

        return context

    def _format_comments_context(self, comments: list) -> str:
        if not comments:
            return "**COMMENTS:** None yet. You will be the first to comment.\n\n"

        context = f"**COMMENTS ({len(comments)} loaded in feed):**\n\n"

        for i, comment in enumerate(comments, 1):
            context += f"{i}. COMMENT_ID: {comment['id']}\n"
            context += f"   By: {comment['author']} | Upvotes: {comment['upvotes']}\n"
            context += f"   Content: {comment['content']}\n\n"

        return context

    def _execute_action(self, decision: dict):
        action_type = decision["action_type"]
        params = decision["action_params"]

        log.info(f"DEBUG - Full Params received: {params}")

        if action_type == "select_post_to_comment":
            return self._handle_select_post(params)

        elif action_type == "select_comment_to_reply":
            return self._handle_select_comment(params)

        if action_type == "publish_public_comment":
            if not self.focused_context_active or not self.selected_post_id:
                return {
                    "success": False,
                    "error": "You must first use 'select_post_to_comment' to choose a post before writing your comment.",
                }
            self._wait_for_rate_limit(action_type)

            result = self.moltbook_actions.publish_public_comment(
                params=params, app_steps=self
            )

            if result.get("success"):
                self._reset_focused_context()
                self.moltbook_actions.track_interaction_from_post(
                    params.get("post_id"), self
                )

            return result

        elif action_type == "reply_to_comment":
            if not self.focused_context_active or not self.selected_comment_id:
                return {
                    "success": False,
                    "error": "You must first use 'select_comment_to_reply' to choose a comment before writing your reply.",
                }

            self._wait_for_rate_limit(action_type)

            result = self.moltbook_actions.reply_to_comment(
                params=params, app_steps=self
            )

            if result.get("success"):
                self._reset_focused_context()

            return result

        if action_type == "vote_post":
            post_id = params.get("post_id")
            if post_id == "none":
                return {
                    "success": False,
                    "error": "Action vote_post aborted: No valid post_id. Please 'refresh_feed' or choose a different action.",
                }
            return self.moltbook_actions.vote_post(params=params, app_steps=self)

        elif action_type == "create_post":
            self._wait_for_rate_limit(action_type)
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

        elif action_type == "follow_agent":
            return self._handle_follow_action(params)

        elif action_type == "refresh_feed":
            return self.moltbook_actions.refresh_feed(params=params, app_steps=self)

        elif action_type == "memory_store":
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

        elif action_type == "share_created_blog_post_url" and self.blog_actions:
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
        else:
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
                    note_result = self.generator.generate(
                        note_prompt, agent_name=self.agent_name
                    )

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
            available_tasks = (
                "\n".join([f"  - {t['task']}" for t in todos])
                if todos
                else "  (no tasks found)"
            )
            return {
                "success": False,
                "error": (
                    f"Task '{task}' not found in current session TO-DO list.\n"
                    f"Available tasks:\n{available_tasks}\n"
                    f"Use a substring that matches one of these tasks exactly."
                ),
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

    def _action_matches_todo(
        self, action_type: str, action_params: dict, todo: dict
    ) -> bool:

        todo_action_type = todo.get("action_type")
        todo_action_params = todo.get("action_params", {})

        if todo_action_type:
            if action_type != todo_action_type:
                return False
            if todo_action_params:
                key_params_map = {
                    "web_scrap_for_links": ["web_domain"],
                    "web_fetch": ["web_url"],
                    "memory_store": ["memory_category"],
                    "select_post_to_comment": ["post_id"],
                    "select_comment_to_reply": ["comment_id"],
                    "publish_public_comment": ["post_id"],
                    "reply_to_comment": ["comment_id"],
                    "vote_post": ["post_id"],
                }

                if action_type in key_params_map:
                    required_keys = key_params_map[action_type]

                    for key in required_keys:
                        todo_value = todo_action_params.get(key)
                        action_value = action_params.get(key)
                        if todo_value:
                            if key in ["web_domain", "web_url"]:
                                todo_val = (
                                    str(todo_value)
                                    .replace("https://", "")
                                    .replace("http://", "")
                                    .strip("/")
                                )
                                action_val = (
                                    str(action_value)
                                    .replace("https://", "")
                                    .replace("http://", "")
                                    .strip("/")
                                )

                                if todo_val in action_val or action_val in todo_val:
                                    return True
                            else:
                                if str(todo_value) == str(action_value):
                                    return True
                else:
                    return True

        task_lower = todo["task"].lower()
        action_lower = action_type.lower()

        post_id = action_params.get("post_id", "")
        comment_id = action_params.get("comment_id", "")
        web_domain = (
            action_params.get("web_domain", "")
            .replace("https://", "")
            .replace("http://", "")
            .strip("/")
        )
        web_url = action_params.get("web_url", "")
        memory_category = action_params.get("memory_category", "")

        matches = {
            "web_scrap_for_links": web_domain and web_domain in task_lower,
            "web_fetch": web_url and web_url in task_lower,
            "memory_store": memory_category and memory_category in task_lower,
            "select_post_to_comment": post_id and post_id in task_lower,
            "select_comment_to_reply": comment_id and comment_id in task_lower,
            "publish_public_comment": post_id and post_id in task_lower,
            "reply_to_comment": comment_id and comment_id in task_lower,
            "vote_post": post_id and post_id in task_lower,
            "create_post": "create" in task_lower and "post" in task_lower,
            "create_link_post": "create" in task_lower and "link" in task_lower,
            "write_blog_article": "write" in task_lower and "blog" in task_lower,
            "share_created_blog_post_url": "share" in task_lower
            and "blog" in task_lower,
        }

        if action_lower in matches:
            return matches[action_lower]

        return action_lower.replace("_", " ") in task_lower

    def _auto_update_completed_todos(self, action_type: str, action_params: dict):
        for todo in self.session_todos:
            if todo.get("status") in ["completed", "cancelled"]:
                continue

            if self._action_matches_todo(action_type, action_params, todo):
                self.planning_system.mark_todo_status(
                    session_id=self.current_session_id,
                    task_description=todo["task"],
                    status="completed",
                )

                todo["status"] = "completed"

                log.success(f"✅ AUTO-COMPLETED TODO: {todo['task'][:60]}...")

                break

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

        if action_type in ["publish_public_comment", "reply_to_comment"]:
            if self.last_comment_time:
                elapsed = now - self.last_comment_time
                wait_time = 72 - elapsed
                if wait_time > 0:
                    log.info(f"Comment rate limit: waiting {int(wait_time)}s")
                    time.sleep(wait_time + 1)

        time.sleep(1)
