import json
import gc
import os
import time
import re
import chromadb
from src.services import (
    MoltbookAPI,
    EmailReporter,
    MemorySystem,
    WebScraper,
    MoltbookActions,
    BlogActions,
    PlanningSystem,
)
from src.generators import Generator, OllamaGenerator
from src.supervisors import Supervisor, SupervisorOllama
from src.utils import log
from src.settings import settings
from src.managers import (
    PromptManager,
    MailManager,
    ToDoManager,
    MasterPlanManager,
    ResearchManager,
    ContextManager,
)
from src.metrics import Metrics
from src.schemas_pydantic import (
    get_pydantic_schema,
    SessionSummary,
)
from src.mocks import (
    LLMMock,
    MoltbookMock,
    MoltbookActionsMock,
    MockMailManager,
    ResearchManagerMock,
)


class AppSteps:
    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        self.remaining_actions = settings.MAX_ACTIONS_PER_SESSION
        self.actions_performed = []
        self.actions_failed = []
        self.actions_rejected = []
        self.actions_aborted = []
        self.created_content_urls = []
        self.session_todos = []
        self.feed_posts_data = {}
        self.feed_comments_data = {}
        self.available_post_ids = []
        self.available_comment_ids = {}
        self.post_creation_attempted = False
        self.blog_article_attempted = False
        self.has_created_master_plan = False
        self.focused_context_active = False
        self.current_active_todo = None
        self.selected_post_id = None
        self.selected_comment_id = None
        self.master_plan_success_prompt = ""
        self.allowed_domains = settings.get_domains()
        self.current_feed = None
        self.reporter = None
        self.last_comment_time = None
        self.to_do_manager = ToDoManager()
        self.context_manager = ContextManager()
        self.master_plan_manager = MasterPlanManager()
        self.blog_actions = (
            BlogActions(self.test_mode) if settings.BLOG_API_URL else None
        )
        if self.test_mode:
            shared_db = "file:testdb?mode=memory&cache=shared"
            mock_data_path = "tests/data/fake_moltbook_api.json"
            if os.path.exists(mock_data_path):
                with open(mock_data_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    log.info(f"🧪 [DEBUG] JSON Keys found: {list(raw_data.keys())}")
                    posts_data = raw_data.get("posts", [])
                    comments_data = raw_data.get("comments", [])

                    self.available_post_ids = [p["id"] for p in posts_data if "id" in p]
                    self.available_comment_ids = {
                        c["id"]: c["post_id"] for c in comments_data if "id" in c
                    }

                    log.info(
                        f"🧪 [MOCK] Feed populated: {len(self.available_post_ids)} posts, {len(self.available_comment_ids)} comments."
                    )
            else:
                log.error(f"❌ Mock JSON file not found at {mock_data_path}")
            self.api = MoltbookMock()
            self.generator = LLMMock()
            self.memory_system = MemorySystem(db_path=shared_db)
            self.planning_system = PlanningSystem(db_path=shared_db)
            self.moltbook_actions = MoltbookActionsMock(db_path=shared_db)
            self.metrics = Metrics()
            self.research_manager = ResearchManagerMock()
            self.prompt_manager = PromptManager()
            self.web_scraper = WebScraper(self.test_mode)
            self.mail_manager = MockMailManager(user="tester@example.com")
            self.agent_name = "MoltbookLocalAgent_TEST"
            log.warning("⚠️ RUNNING IN OFFLINE TEST MODE")
        else:
            self.api = MoltbookAPI()
            if settings.USE_OLLAMA:
                self.generator = OllamaGenerator(model=settings.OLLAMA_MODEL)
                self.supervisor = SupervisorOllama(model=settings.OLLAMA_MODEL)
            else:
                self.generator = Generator()
                self.supervisor = Supervisor(self.generator.llm)
            self.reporter = EmailReporter()
            self.memory_system = MemorySystem(db_path=settings.DB_PATH)
            self.prompt_manager = PromptManager()
            self.planning_system = PlanningSystem(db_path=settings.DB_PATH)
            self.web_scraper = WebScraper()
            self.metrics = Metrics()
            chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
            collection = chroma_client.get_or_create_collection(name="knowledge")
            self.research_manager = ResearchManager(
                scraper=self.web_scraper,
                vector_db=collection,
                llm_client=self.generator.llm,
            )
            self.mail_manager = None
            if settings.AGENT_IMAP_SERVER:
                self.mail_manager = MailManager(
                    host=settings.AGENT_IMAP_SERVER,
                    user=settings.AGENT_MAIL_BOX_EMAIL,
                    password=settings.AGENT_MAIL_BOX_PASSWORD,
                )
            self.agent_name = "Agent"
            self.cached_dynamic_context = ""
            self.moltbook_actions = MoltbookActions(db_path=settings.DB_PATH)
            self.feed_options = ["top", "hot", "new", "rising"]
            self.available_submolts = ["general"]
            self.last_post_time = None
            self.current_session_id = None
            self.current_prompt = None

    def run_session(self):
        log.info("=== SESSION START ===")
        result = self.context_manager.get_context(self)
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
        self.current_session_id = self.memory_system.create_session()

        last_pub_status = None
        if settings.BLOG_API_URL:
            last_pub_status = self.memory_system.get_last_session_publication_status(
                current_session_id=self.current_session_id
            )
            if last_pub_status:
                log.info(
                    f"📊 Last session published - Blog: {last_pub_status['has_published_blog']}, Post: {last_pub_status['has_published_post']}"
                )

        if not self.master_plan_manager.ensure_master_plan(app_steps=self):
            master_plan_just_created = True
            result = self.context_manager.get_context(self)
            if not result:
                return
            system_context, dynamic_context, agent_name, current_karma = result
            self.generator.conversation_history[0] = {
                "role": "system",
                "content": self.generator.get_main_system_prompt()
                + f"\n\n{system_context}",
            }
            self.has_created_master_plan = True

        self.current_prompt, self.session_todos = (
            self.to_do_manager.create_session_plan(
                prompt_manager=self.prompt_manager,
                generator=self.generator,
                agent_name=self.agent_name,
                master_plan_success_prompt=self.master_plan_success_prompt,
                planning_system=self.planning_system,
                current_session_id=self.current_session_id,
                dynamic_context="" if master_plan_just_created else dynamic_context,
                last_publication_status=last_pub_status,
            )
        )
        required_actions = self.to_do_manager.calculate_required_actions(app_steps=self)
        self.remaining_actions = required_actions

        log.info(
            f"📊 Session plan: {len(self.session_todos)} tasks requiring ~{required_actions} actions"
        )
        log.info(f"🎯 Action budget allocated: {self.remaining_actions}")

        pending_confirmation = "### ✅ SESSION PLAN LOADED\n"
        pending_confirmation += (
            f"**TASKS:** {', '.join([t['task'] for t in self.session_todos])}\n\n"
        )

        while self.remaining_actions > 0:
            pending_confirmation = self._perform_autonomous_action(
                extra_feedback=pending_confirmation
            )
            if (
                isinstance(pending_confirmation, dict)
                and pending_confirmation.get("action_type") == "TERMINATE_SESSION"
            ):
                log.info("Agent decided to terminate session early.")
                unfinished_tasks = [
                    t
                    for t in self.session_todos
                    if t.get("status") not in ["completed", "failed"]
                ]
                for task in unfinished_tasks:
                    self.actions_aborted.append(
                        {"action": task["task"], "reason": "session_terminated"}
                    )

                log.info(
                    f"📉 Marked {len(unfinished_tasks)} remaining tasks as aborted."
                )
                break

        log.info("Generating session summary...")

        self.current_prompt = self.prompt_manager.get_summary_prompt(
            agent_name=self.agent_name, actions_performed=self.actions_performed
        )
        summary_raw = self.generator.generate_session_summary(
            self.current_prompt,
            pydantic_model=SessionSummary,
            agent_name=self.agent_name,
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
            self.actions_performed,
            self.actions_failed,
            self.actions_rejected,
            self.actions_aborted,
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

            self.memory_system.store_session_metrics(
                session_id=self.current_session_id,
                total_actions=session_metrics["total_actions"],
                successful_actions=session_metrics["success_count"],
                supervisor_rejections=session_metrics["supervisor_rejections"],
                execution_failures=session_metrics["execution_failures"],
                aborted_tasks=session_metrics["aborted_tasks"],
                session_score=session_metrics["session_score"],
                supervisor_verdict=supervisor_verdict_text,
                supervisor_grade=supervisor_grade_text,
            )

        self.memory_system.save_session(
            summary=summary,
            actions_performed=self.actions_performed,
            conversation_history=self.generator.conversation_history,
            session_id=self.current_session_id,
        )

        global_progression = self.metrics._calculate_global_progression(self)
        log.info(
            f"📊 Global progression: {global_progression['global_score']:.1f}% "
            f"({global_progression['trend']}, {global_progression['progression_rate']:+.1f}%)"
        )

        self.master_plan_manager.update_master_plan_if_needed(summary, app_steps=self)

        if self.reporter:
            self.reporter.send_session_report(
                agent_name=agent_name,
                karma=current_karma,
                learnings=summary["learnings"],
                next_plan=summary["next_session_plan"],
                content_urls=self.created_content_urls,
                session_metrics=session_metrics,
                supervisor_verdict=(
                    supervisor_verdict if settings.USE_SUPERVISOR else None
                ),
                global_progression=global_progression,
                actions_performed=self.actions_performed,
                actions_failed=self.actions_failed,
                actions_aborted=self.actions_aborted,
                actions_rejected=self.actions_rejected,
            )

        if self.test_mode:
            self.shutdown_test_mode()

        log.info("=== SESSION END ===")

    def shutdown_test_mode(self):
        log.info("Initiating test mode shutdown...")

        try:
            if hasattr(self, "memory_system"):
                self.memory_system.conn.close()
            if hasattr(self, "planning_system"):
                self.planning_system.conn.close()
            if hasattr(self, "moltbook_actions"):
                self.moltbook_actions.conn.close()
        except Exception as e:
            log.error(f"⚠️ Error closing DB connections: {e}")

        gc.collect()
        self.cleanup_test_db()

    def cleanup_test_db(self):
        garbage_files = ["file", "file:testdb?mode=memory&cache=shared"]
        for f in garbage_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    log.info(f"🧹 Cleanup: Removed temporary file {f}")
                except Exception as e:
                    log.error(f"❌ Failed to delete {f}: {e}")

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
            "research_recursive",
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

        if self.mail_manager:
            allowed_actions.extend(
                [
                    "email_read",
                    "email_send",
                    "email_delete",
                    "email_archive",
                    "email_mark_read",
                ]
            )

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

        if self.focused_context_active:
            if self.selected_post_id and not any(
                isinstance(a, dict) and a.get("action_type") == "publish_public_comment"
                for a in self.actions_performed
            ):
                allowed_actions = ["publish_public_comment"]
                log.warning(
                    f"🔒 FORCED MODE: Only publish_public_comment is allowed (post selected)"
                )

            elif self.selected_comment_id and not any(
                isinstance(a, dict) and a.get("action_type") == "reply_to_comment"
                for a in self.actions_performed
            ):
                allowed_actions = ["reply_to_comment"]
                log.warning(
                    f"🔒 FORCED MODE: Only reply_to_comment is allowed (comment selected)"
                )

        for attempt in range(1, max_attempts + 1):
            heavy_payload = ""
            strategic_parts = []
            attempts_left = (max_attempts - attempt) + 1
            if self.focused_context_active:
                focused_context = self.context_manager.get_focused_post_context(
                    app_steps=self,
                    post_id=self.selected_post_id,
                    target_comment_id=self.selected_comment_id,
                )

                heavy_payload = focused_context

            else:
                if self.current_feed:
                    heavy_payload = (
                        f"# 🌍 CURRENT WORLD STATE\n{self.cached_dynamic_context}"
                    )

            if attempt == 1 and extra_feedback:
                strategic_parts.append(f"{extra_feedback}")

            if attempt > 1:
                critical_error_block = self.prompt_manager.get_critical_error_block(
                    attempt=attempt,
                    decision=decision,
                    last_error=last_error,
                    attempts_left=attempts_left,
                )
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

            if attempts_left != 1:
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

            action_constraint = f"""
╔══════════════════════════════════════════════════════════════╗
║  ⚠️ AVAILABLE ACTIONS FOR THIS TURN
╚══════════════════════════════════════════════════════════════╝

**YOU CAN ONLY USE ONE OF THESE ACTIONS:**
{chr(10).join(f"- {action}" for action in allowed_actions)}

**ANY OTHER ACTION WILL BE REJECTED IMMEDIATELY.**
"""
            strategic_parts.insert(0, action_constraint)

            self.current_prompt = "\n".join(strategic_parts)

            try:
                expected_action = (
                    self.current_active_todo.get("action_type")
                    if self.current_active_todo
                    else None
                )
                if self.focused_context_active:
                    if self.selected_post_id:
                        expected_action = "publish_public_comment"
                    elif self.selected_comment_id:
                        expected_action = "reply_to_comment"
                pydantic_model = (
                    get_pydantic_schema(expected_action) if expected_action else None
                )

                result = self.generator.generate(
                    self.current_prompt,
                    pydantic_model=pydantic_model,
                    agent_name=self.agent_name,
                    heavy_context=heavy_payload,
                )
                self.generator.trim_history(
                    has_created_master_plan=self.has_created_master_plan
                )
                content = result["choices"][0]["message"]["content"]
                content = re.sub(r"```json\s*|```\s*", "", content).strip()
                if isinstance(content, str):
                    decision = json.loads(content)
                else:
                    decision = content

                action_type = decision.get("action_type")

                if action_type not in allowed_actions:
                    error_msg = (
                        f"❌ PROTOCOL ERROR: Action '{action_type}' is not authorized in this context.\n"
                        f"Available actions are: {', '.join(allowed_actions)}.\n"
                        f"Please verify your workflow sequence and choose a valid tool."
                    )

                    log.error(
                        f"🚨 INVALID ACTION: Agent attempted '{action_type}' (Not in allowed_actions)"
                    )

                    last_error = f"{error_msg}\n⚠️ WARNING: {attempts_left} attempts remaining before session termination."

                    if attempt < max_attempts:
                        continue
                    else:
                        break

                if action_type == "publish_public_comment":
                    if not self.selected_post_id:
                        last_error = self.prompt_manager.get_publish_public_comment_phase_2_protocol_error(
                            attempts_left=attempts_left
                        )
                        log.error(
                            f"🚨 WORKFLOW VIOLATION: Attempted publish_public_comment without selecting post first"
                        )
                        if attempt < max_attempts:
                            continue
                        else:
                            break

                if action_type == "reply_to_comment":
                    if not self.selected_comment_id:
                        last_error = self.prompt_manager.get_reply_to_comment_phase_2_protocol_error(
                            attempts_left=attempts_left
                        )
                        log.error(
                            f"🚨 WORKFLOW VIOLATION: Attempted reply_to_comment without selecting comment first"
                        )
                        if attempt < max_attempts:
                            continue
                        else:
                            break

                if action_type == "select_post_to_comment" and self.selected_post_id:
                    if self.focused_context_active:
                        last_error = self.prompt_manager.get_confusion_error_on_select_post_to_comment(
                            selected_post_id=self.selected_post_id,
                            attempts_left=attempts_left,
                        )
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
                        last_error = (
                            self.prompt_manager.get_confusion_error_on_reply_to_comment(
                                selected_comment_id=self.selected_comment_id,
                                attempts_left=attempts_left,
                            )
                        )
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

                    if not audit_report["is_valid"]:
                        last_error = f"**🤖 SUPERVISOR REJECTION:** {audit_report['message_for_agent']}"
                        self.actions_rejected.append(
                            {
                                "action": action_type,
                                "attempt": attempt,
                                "reason": last_error,
                            }
                        )
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

                if self.current_active_todo:
                    is_match = self.to_do_manager.action_matches_todo(
                        action_type=decision.get("action_type"),
                        action_params=decision.get("action_params", {}),
                        todo=self.current_active_todo,
                    )

                    if not is_match:
                        todo_params = (
                            self.current_active_todo.get("action_params", {}) or {}
                        )
                        act_params = decision.get("action_params", {}) or {}

                        mismatches = []

                        for key, expected_val in todo_params.items():
                            actual_val = act_params.get(key)
                            if str(expected_val) != str(actual_val):
                                mismatches.append(
                                    f"- `{key}`: Expected `{expected_val}`, got `{actual_val}`"
                                )

                        is_last_chance = attempt == max_attempts - 1
                        warning_header = (
                            "🚨 **FINAL WARNING: LOGIC LOOP DETECTED** 🚨"
                            if is_last_chance
                            else "🚨 **CRITICAL TASK PARAMETER MISMATCH** 🚨"
                        )
                        mismatch_details = (
                            "\n".join(mismatches)
                            if mismatches
                            else "- Parameter structure mismatch."
                        )

                        last_error = f"""
{warning_header}

Your proposed action does not align with the requirements of your Active Task.
**Divergences detected:**
{mismatch_details}

**REQUIRED ACTION TYPE:** `{self.current_active_todo.get('action_type')}`
"""
                        if is_last_chance:
                            last_error += f"""
⚠️ **TERMINATION PROTOCOL INITIATED:**
You have failed this ID match twice. You are currently anchored to an incorrect ID `{act_params.get('post_id', 'N/A')}`.
This is your **LAST CHANCE**. 

**DIRECTIVE:**
- Copy/Paste the expected value: `{todo_params.get('post_id', 'N/A')}`.
- If you repeat the same wrong ID again, Task '{self.current_active_todo.get('task')[:30]}' will be MARKED AS FAILED and you will lose access to this thread.
- If the expected ID is missing from your feed, use `update_todo_status` to CANCEL this task NOW.
"""
                        else:
                            last_error += """
**FIX:**
1. Use the EXACT parameters defined in your Session Plan.
2. If the target is no longer accessible, use `update_todo_status` to mark as 'cancelled'.
"""
                        log.error(
                            f"🚫 Action blocked: Parameter Mismatch for task '{self.current_active_todo.get('task')[:30]}'"
                        )

                        if attempt < max_attempts:
                            continue
                        else:
                            break

                execution_result = self._execute_action(decision)

                if not execution_result:
                    last_error = "INTERNAL ERROR: Action returned None (should return dict with 'success' key)"
                    log.error(last_error)
                    continue
                if execution_result.get("error"):
                    last_error = execution_result["error"]
                    self.actions_failed.append(
                        {"action": action_type, "error": last_error}
                    )
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
                self.to_do_manager.auto_update_completed_todos(
                    action_type=decision["action_type"],
                    action_params=decision.get("action_params", {}),
                    session_todos=self.session_todos,
                    current_session_id=self.current_session_id,
                    planning_system=self.planning_system,
                    app_steps=self,
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
                last_error = None
                break

            except (json.JSONDecodeError, KeyError) as e:
                raw_response = getattr(
                    self.generator, "last_raw_response", "Unavailable"
                )
                last_error = f"JSON/Parsing Error: {str(e)}"

                log.error(f"💥 JSON Syntax Error detected! Skipping current attempt.")
                log.error(f"📄 Raw Data causing error: {raw_response}...")

                self.actions_failed.append(
                    {
                        "action": "parsing_error",
                        "error": last_error,
                        "raw_data": raw_response[:200],
                    }
                )

                if attempt >= max_attempts:
                    feedback = f"❌ **CRITICAL PARSING ERROR:** Your last response was not valid JSON.\n"
                    feedback += "⚠️ ACTION: You must change your output format immediately. Try a different task or action type."
                    self.remaining_actions -= 1
                    return feedback

        if decision and last_error:
            action_name = decision.get("action_type", "UNKNOWN")
            log.error(
                f"❌ Action '{action_name}' failed after {max_attempts} attempts. FORCING PIVOT."
            )
            self.actions_failed.append(
                {"action": action_type, "final_error": last_error}
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

    def _execute_action(self, decision: dict):
        action_type = decision["action_type"]
        params = decision["action_params"]

        log.info(f"DEBUG - Full Params received: {params}")

        if action_type == "select_post_to_comment":
            return self.context_manager.handle_select_post(params, app_steps=self)

        elif action_type == "select_comment_to_reply":
            return self.context_manager.handle_select_comment(params, app_steps=self)

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
                self.context_manager.reset_focused_context(self)
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
            return self.to_do_manager.handle_todo_update(
                params,
                planning_system=self.planning_system,
                actions_performed=self.actions_performed,
                current_session_id=self.current_session_id,
            )

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

        elif action_type == "email_read":
            return self.mail_manager.get_messages(params=params)

        elif action_type == "email_send":
            return self.mail_manager.send_email(params=params)

        elif action_type == "email_delete":
            return self.mail_manager.delete_emails(params=params)

        elif action_type == "email_archive":
            return self.mail_manager.archive_email(params=params)

        elif action_type == "email_mark_read":
            return self.mail_manager.mark_as_read(params=params)

        if action_type == "research_recursive":
            objective = decision.get("action_params", {}).get("objective")
            research_report = self.research_manager.conduct_deep_research(objective)
            self.memory_system.store_internal_note(
                self.current_session_id, research_report
            )
            return {
                "status": "success",
                "summary": "Deep research completed and vectorized.",
            }
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

    def _handle_view_summaries(self, params: dict):
        limit = params.get("summary_limit", 5)

        summaries = self.memory_system.get_session_history(limit=limit)

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
