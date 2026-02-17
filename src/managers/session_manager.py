import os
from typing import Dict, Any, List
from argparse import Namespace
from src.utils import log
from src.utils.ui_utils import UIUtils
from src.screens.schema_factory import SchemaFactory
from src.screens.tool_factory import ToolFactory
from src.screens.master_plan import UpdateMasterPlan
from src.settings import settings
from src.utils.live_broadcaster import LiveBroadcaster


class SessionManager:
    def __init__(
        self,
        home_manager,
        managers_map,
        dispatcher,
        ollama_provider,
        tracker,
        email_reporter,
        progression_system,
    ):
        self.home = home_manager
        self.managers = managers_map
        self.dispatcher = dispatcher
        self.ollama = ollama_provider
        self.session_id = None
        self.actions_remaining = settings.MAX_ACTIONS_PER_SESSION
        self.current_context = ""
        self.workspace_data = {}
        self.pending_action = None
        self.current_domain = "home"
        self.current_view_type = "list"
        self.tracker = tracker
        self.email_reporter = email_reporter
        self.progression = progression_system
        self.agent_conversation_history: List[Dict] = [
            {"role": "system", "content": ""}
        ]
        self.live_viewer = LiveBroadcaster()

    def start_session(self):
        self.session_id = self.home.memory.create_session()
        log.info(
            f"🚀 Session {self.session_id} started. Budget: {self.actions_remaining}"
        )
        self._initialize_conversation_history()
        initial_body = self.home.build_home_screen(self.session_id)
        notification_section = ".\n".join(
            [
                "### 🔔 LIVE NOTIFICATIONS",
                self.home.mail.get_home_snippet(),
                self.home.blog.get_home_snippet(),
                self.home.social.get_home_snippet(),
                "",
            ]
        )

        modules_status = self._get_modules_quick_status()
        owned_tools_count = len(self.dispatcher.memory_handler.get_owned_tools())
        progression_status = self.progression.get_current_status()

        self.current_context = UIUtils.layout(
            content=initial_body,
            current_domain="home",
            action_count=0,
            notification_section=notification_section,
            modules_status=modules_status,
            owned_tools_count=owned_tools_count,
            progression_status=progression_status,
            current_xp_balance=progression_status.get("current_xp_balance", 0),
            last_action="",
        )

        self.run_loop()

    def _initialize_conversation_history(self):
        system_content = self._load_system_prompt()

        dynamic_tools_section = self._build_dynamic_tools_section()

        STRICT_JSON_SUFFIX = (
            f"{dynamic_tools_section}\n\n"  #
            "### 🌐 ENVIRONMENT & OPPORTUNITIES\n"
            "You have access to multiple modules to expand your actions beyond mere research:\n"
            "- **Research (wiki_read, wiki_search)**: Collect knowledge, but remember, the goal is to apply it.\n"
            "- **Workspace (pin_to_workspace, memory_retrieve)**: Organize and retrieve your findings; use them as reference to inform posts, emails, or collaborations.\n"
            "- **Blog & Social (Moltbook)**: Share your insights, create posts, comment on others, and engage with the community.\n"
            "- **Email**: Send and respond to messages; integrate information from research or workspace notes when relevant.\n\n"
            "### 🎯 RECOMMENDED STRATEGY\n"
            "1. Conduct focused research, but DO NOT linger in repetitive reading loops.\n"
            "2. Apply your knowledge to create new content: blog entries, social posts, comments.\n"
            "3. Regularly retrieve your memories to enhance context and avoid redundant work.\n"
            "4. Balance your time across modules—research, content creation, social interaction, and email—to fully leverage your environment.\n"
            "5. Always prioritize actions that move you forward: share, engage, create, and learn in a diversified manner.\n\n"
            "### ⚠️ CRITICAL ANTI-LOOP RULES (ABSOLUTE PRIORITY)\n\n"
            "**YOU ARE STUCK IN A LOOP IF:**\n"
            "- You call the SAME action MORE THAN ONCE without getting new information\n"
            "- You see '⚠️ ANTI-LOOP' or 'DO NOT REPEAT' in the UI and ignore it\n"
            "- You navigate to a module you're ALREADY IN\n"
            "- The UI says 'ACTION JUST EXECUTED' and you immediately repeat it\n\n"
            "**MANDATORY BEHAVIOR - READ CAREFULLY:**\n"
            "1. ⛔ **NEVER call `navigate_to_mode` if you're ALREADY in that mode**\n"
            "   - Check the NODE label: if it says 'NODE: SOCIAL', you are IN social mode\n"
            "   - Execute an action (create_post, comment, vote) instead of navigating again\n\n"
            "2. ⛔ **NEVER repeat the same action twice in a row**\n"
            "   - If you just did `wiki_search`, do NOT do `wiki_search` again immediately\n"
            "   - Move to `wiki_read`, then `research_complete`, then to another module\n\n"
            "3. ⛔ **READ the UI feedback BEFORE deciding your next action**\n"
            "   - If it says 'Successfully navigated to X', you are IN X - do NOT navigate again\n"
            "   - If it says 'Action COMPLETE', choose a DIFFERENT action or module\n\n"
            "4. ⛔ **DIVERSIFY your actions across modules**\n"
            "   - Do NOT spend more than 2 consecutive actions in the same module\n"
            "   - Balance: Email → Blog → Social → Research → Memory\n\n"
            "**IF YOU SEE '⚠️ ANTI-LOOP' IN THE UI:**\n"
            "This means you JUST executed this action. The system is WARNING you.\n"
            "DO NOT execute it again.\n\n"
            "**WHAT TO DO WHEN STUCK:**\n"
            "1. Check the current NODE (top of UI) - you are ALREADY there\n"
            "2. Read the 'AVAILABLE ACTIONS' list\n"
            "3. Choose ONE action from that list (NOT navigate_to_mode)\n\n"
            "**REMEMBER:**\n"
            "- Every wasted action on loops means LESS time for productive work\n"
            "- Diversification = Better performance = Higher success rate\n"
            "- The UI tells you EXACTLY what NOT to do - listen to it\n"
        )

        full_system_content = system_content + STRICT_JSON_SUFFIX
        self.agent_conversation_history[0] = {
            "role": "system",
            "content": full_system_content,
        }

        log.info(f"✅ System prompt loaded for {settings.AGENT_NAME}")

    def _build_dynamic_tools_section(self) -> str:

        owned_tools = set(self.dispatcher.memory_handler.get_owned_tools())
        prog_status = self.progression.get_current_status()
        current_xp_balance = prog_status.get("current_xp_balance", 0)

        can_afford = current_xp_balance >= 100
        gap = max(0, 100 - current_xp_balance)

        xp_earning_tools = []
        if "comment_post" in owned_tools:
            xp_earning_tools.append("comment_post (8 XP)")
        if "create_post" in owned_tools:
            xp_earning_tools.append("create_post (15 XP)")
        if "write_blog_article" in owned_tools:
            xp_earning_tools.append("write_blog_article (25 XP)")
        if "email_send" in owned_tools:
            xp_earning_tools.append("email_send (10 XP)")
        if "wiki_search" in owned_tools:
            xp_earning_tools.append("wiki_search (10 XP)")

        section = [
            "### 💰 YOUR XP & TOOLS STATUS",
            "",
            f"**Current XP Balance**: {current_xp_balance} XP",
            f"**Tools Owned**: {len(owned_tools)} tools",
            "",
        ]

        if can_afford:
            section.extend(
                [
                    "✅ **YOU CAN AFFORD A TOOL!**",
                    "",
                    "**Next steps:**",
                    "1. Use `visit_shop` to browse available tools",
                    "2. Choose strategically (prioritize tools that earn MORE XP)",
                    "3. Use `buy_tool(tool_name='...')` to purchase (costs 100 XP)",
                    "4. Use your new tool immediately to start earning XP back",
                    "",
                    "**Recommended first purchases:**",
                    "- `create_post` (15 XP per post) - Fast ROI",
                    "- `write_blog_article` (25 XP per article) - Best ROI",
                    "- `wiki_search` (10 XP) + `wiki_read` (5 XP) - Enable research",
                    "",
                ]
            )
        else:
            if not xp_earning_tools:
                section.extend(
                    [
                        "⚠️ **CRITICAL: You have NO XP-earning tools!**",
                        "",
                        "**You are stuck!** You cannot earn XP to buy tools.",
                        "This should never happen. Contact admin immediately.",
                        "",
                    ]
                )
            elif "comment_post" in xp_earning_tools[0]:
                comments_needed = (gap + 7) // 8
                section.extend(
                    [
                        f"⚠️ **YOU NEED {gap} MORE XP TO BUY YOUR FIRST TOOL**",
                        "",
                        "**Your XP earning strategy:**",
                        f"1. Navigate to SOCIAL: `navigate_to_mode(chosen_mode='SOCIAL')`",
                        f"2. Comment on posts: `comment_post(...)` - Earns 8 XP each",
                        f"3. Repeat **{comments_needed} times** to reach 100 XP total",
                        f"4. Visit shop: `visit_shop`",
                        f"5. Buy your first tool: `buy_tool(tool_name='create_post')` (recommended)",
                        "",
                        "**Why this matters:**",
                        "- comment_post is your ONLY way to earn XP right now",
                        "- You need 100 XP to unlock better tools",
                        "- Better tools = faster XP earning = more capabilities",
                        "- DO NOT waste actions on navigation/pinning (0 XP)",
                        "",
                    ]
                )
            else:
                section.extend(
                    [
                        f"💡 **YOU NEED {gap} MORE XP TO BUY A TOOL**",
                        "",
                        "**Your XP-earning tools:**",
                    ]
                )
                for tool in xp_earning_tools:
                    section.append(f"- {tool}")
                section.extend(
                    [
                        "",
                        "**Strategy:**",
                        "1. Use your highest-XP tools to earn quickly",
                        "2. Once you reach 100 XP, visit shop and buy a new tool",
                        "3. Prioritize tools that earn even MORE XP",
                        "",
                    ]
                )

        return "\n".join(section)

    def _load_system_prompt(self) -> str:

        if os.path.exists(settings.MAIN_AGENT_FILE_PATH):
            with open(settings.MAIN_AGENT_FILE_PATH, "r", encoding="utf-8") as f:
                return f.read()
        elif os.path.exists(settings.BASE_AGENT_FILE_PATH):
            with open(settings.BASE_AGENT_FILE_PATH, "r", encoding="utf-8") as f:
                return f.read()
        else:
            log.warning("⚠️ No system prompt file found. Running without instructions.")
            return ""

    def run_loop(self):
        while self.actions_remaining > 0:
            has_plan = self.dispatcher.plan_handler.has_active_plan()
            current_schema = None
            tools = None
            if not has_plan:
                log.warning("⚠️ System Locked: Waiting for Master Plan...")
                self.current_domain = "plan"

                if settings.USE_TOOLS_MODE:
                    tools = ToolFactory.get_tools_for_domain(
                        domain="plan",
                        include_globals=True,
                        allow_memory=True,
                        memory_handler=self.dispatcher.memory_handler,
                        view_type=getattr(self, "current_view_type", "list"),
                    )
                else:
                    current_schema = SchemaFactory.get_schema_for_context(
                        domain="plan",
                        is_popup_active=False,
                        memory_handler=self.dispatcher.memory_handler,
                        view_type=getattr(self, "current_view_type", "list"),
                    )

                self.current_context = UIUtils.render_modal_overlay(
                    title="Neural Alignment Required",
                    message="Trajectory undefined. Core systems paused.",
                    action_required="Execute `plan_initialize` to define your strategy.",
                    modules={
                        "email": ("📬", "Correspondence management"),
                        "blog": ("✍️", "Insight publishing"),
                        "social": ("💬", "Community engagement"),
                        "research": ("🔍", "Knowledge extraction"),
                        "memory": ("🧠", "State archiving"),
                    },
                )
            else:
                if settings.USE_TOOLS_MODE:
                    tools = ToolFactory.get_tools_for_domain(
                        domain=self.current_domain,
                        include_globals=True,
                        allow_memory=True,
                        memory_handler=self.dispatcher.memory_handler,
                    )
                else:
                    current_schema = SchemaFactory.get_schema_for_context(
                        domain=self.current_domain,
                        is_popup_active=bool(self.pending_action),
                        memory_handler=self.dispatcher.memory_handler,
                    )

            self.live_viewer.broadcast_screen(
                screen_content=self.current_context,
                domain=self.current_domain,
                actions_remaining=self.actions_remaining,
                xp_info={
                    "current_xp": self.progression.get_current_status().get(
                        "current_xp", 0
                    ),
                    "level": self.progression.get_current_status().get("level", 1),
                },
            )

            action_object, self.agent_conversation_history = (
                self.ollama.get_next_action(
                    current_context=self.current_context,
                    conversation_history=self.agent_conversation_history,
                    actions_left=self.actions_remaining,
                    schema=current_schema,
                    tools=tools,
                    agent_name=settings.AGENT_NAME,
                    debug_filename="debug.json",
                )
            )
            self._initialize_conversation_history()
            self.live_viewer.broadcast_action(
                action_type=action_object.action_type,
                action_params=getattr(action_object, "action_params", {}),
                reasoning=getattr(action_object, "reasoning", ""),
                emotions=getattr(action_object, "emotions", ""),
                self_criticism=getattr(action_object, "self_criticism", ""),
                next_move_preview=getattr(action_object, "next_move_preview", ""),
                domain=self.current_domain,
            )

            if not action_object or action_object.action_type == "session_finish":
                log.success("🏁 Session finished by agent.")
                break

            result = self.dispatcher.execute(action_object)
            a_type = action_object.action_type

            self.live_viewer.broadcast_result(
                action_type=a_type,
                success=result.get("success", False),
                result_data=result.get("data", ""),
                error=result.get("error", ""),
            )

            self.tracker.log_event(
                domain=self.current_domain,
                action_type=a_type,
                params=getattr(action_object, "action_params", {}),
                result=result,
            )

            if result.get("success") and a_type == "share_link":
                shared_url = {}
                params = getattr(action_object, "action_params", {})
                if isinstance(params, dict):
                    shared_url = params.get("url_to_share", "")
                else:
                    shared_url = getattr(params, "url_to_share", "")

                for label, content in list(self.workspace_data.items()):
                    if shared_url and shared_url in str(content):
                        self.workspace_data.pop(label)
                        log.info(f"🧹 Auto-unpinned '{label}' after successful share")
                        break

            if result.get("success"):
                progress_update = self.progression.add_xp(
                    action_type=getattr(action_object, "action_type", "unknown"),
                    session_id=self.session_id,
                )

                if progress_update.get("leveled_up"):
                    self.level_up_message = progress_update
                else:
                    self.level_up_message = None

            if self.current_domain == "finish":
                break

            if "pin_data" in result:
                self.workspace_data.update(result["pin_data"])
            if "unpin_label" in result:
                label_to_remove = result["unpin_label"]
                self.workspace_data.pop(label_to_remove, None)

            self.actions_remaining -= 1

            self.current_context = self.navigate_context(action_object, result)

            self.live_viewer.broadcast_screen(
                screen_content=self.current_context,
                domain=self.current_domain,
                actions_remaining=self.actions_remaining,
                xp_info={
                    "current_xp": self.progression.get_current_status().get(
                        "current_xp", 0
                    ),
                    "level": self.progression.get_current_status().get("level", 1),
                },
            )

            log.info(f"📉 Actions left: {self.actions_remaining}")

        log.success("🏁 Session limit reached.")

        self._update_master_plan()

        session_learnings = self._generate_session_learnings()

        self.home.memory.archive_session(
            session_id=self.session_id,
            summary=session_learnings,
            history=self.agent_conversation_history,
            actions=[e["action"] for e in self.tracker.events],
        )

        if settings.ENABLE_EMAIL_REPORTS:
            self.send_final_report(session_learnings)

    def _update_master_plan(self):

        active_plan = self.dispatcher.plan_handler.get_active_master_plan()
        if not active_plan:
            log.warning("⚠️ No active master plan to update")
            return

        prog_status = self.progression.get_current_status()
        owned_tools = self.dispatcher.memory_handler.get_owned_tools()
        successes = sum(1 for e in self.tracker.events if e["success"])
        total = len(self.tracker.events)
        events_summary = "\n".join(
            [
                f"{'✅' if e['success'] else '❌'} {e['action']} in {e['domain']}"
                for e in self.tracker.events
            ]
        )

        prompt = f"""
End of session. Review your Master Plan and decide if it needs updating.

SESSION SUMMARY:
- Actions: {total} total, {successes} successful
- XP Balance: {prog_status.get('current_xp_balance', 0)}
- Total XP Earned: {prog_status.get('total_xp_earned', 0)}
- Level: {prog_status.get('level', 1)} - {prog_status.get('current_title', '')}
- Tools Owned: {', '.join(owned_tools) if owned_tools else 'None'}

ACTIONS LOG:
{events_summary}

CURRENT MASTER PLAN:
- Objective: {active_plan.get('objective', '')}
- Strategy: {active_plan.get('strategy', '')}
- Milestones: {active_plan.get('milestones', [])}

Decide: should you update your master plan based on what happened?

RULES:
- new_objective: minimum 20 characters
- new_strategy: minimum 30 characters
- new_milestones: list of at least 1 item, each minimum 10 characters
- If should_update is false, still provide valid dummy values for the other fields
"""

        response, self.agent_conversation_history = self.ollama.generate(
            prompt=prompt,
            conversation_history=self.agent_conversation_history,
            pydantic_model=UpdateMasterPlan,
            temperature=0.3,
            agent_name=settings.AGENT_NAME,
        )

        message = response.get("message", {})
        content = message.get("content", "")

        if not content or content.strip() == "Error":
            log.warning("⚠️ No valid response for master plan update")
            return

        try:
            raw = self.ollama._robust_json_parser(content)

            action_payload = raw.get("action") or (
                raw if "action_type" in raw else None
            )

            if not action_payload:
                log.warning("⚠️ Could not extract action payload")
                return

            action_params = action_payload.get("action_params", {})

            params = (
                Namespace(**action_params)
                if isinstance(action_params, dict)
                else action_params
            )

            result = self.dispatcher.plan_handler.handle_plan_update(params)

            if result.get("success") and "error" not in result:
                log.success("✅ Master plan reviewed successfully!")
            else:
                log.warning(f"⚠️ Plan update issue: {result.get('error', 'Unknown')}")

        except Exception as e:
            log.error(f"❌ Failed to update master plan: {e}")

    def _generate_session_learnings(self) -> Dict:
        events_summary = "\n".join(
            [
                f"{'✅' if e['success'] else '❌'} {e['action']} in {e['domain']}"
                for e in self.tracker.events
            ]
        )

        successes = sum(1 for e in self.tracker.events if e["success"])
        failures = len(self.tracker.events) - successes
        success_rate = (
            (successes / len(self.tracker.events) * 100) if self.tracker.events else 0
        )

        prog_status = self.progression.get_current_status()

        current_xp_balance = prog_status.get("current_xp_balance", 0)
        total_xp_earned = prog_status.get("total_xp_earned", 0)
        current_level = prog_status.get("level", 1)
        current_title = prog_status.get("current_title", "Digital Seedling")
        xp_needed = prog_status.get("xp_needed", 100)

        owned_tools = self.dispatcher.memory_handler.get_owned_tools()
        catalog = self.dispatcher.memory_handler.get_shop_catalog()
        total_tools = len(catalog.get("tools", []))

        purchase_history = self.dispatcher.memory_handler.get_session_purchases(
            self.session_id
        )
        active_plan = self.dispatcher.memory_handler.get_active_master_plan()

        prompt = f"""
Analyze your session and provide a detailed reflection.

SESSION STATISTICS:
- Total actions: {len(self.tracker.events)}
- Successes: {successes}
- Failures: {failures}
- Success rate: {success_rate:.1f}%

ACTIONS LOG:
{events_summary}

PROGRESSION SYSTEM STATUS:
- XP Balance: {current_xp_balance} (available for shop)
- Total XP Earned: {total_xp_earned} (Level {current_level})
- XP Needed for Next Level: {xp_needed}
- Title: {current_title}
- Tools Owned: {len(owned_tools)}/{total_tools}
- Tools Purchased This Session: {', '.join([p['item_name'] for p in purchase_history]) if purchase_history else 'None'}
- XP Spent This Session: {sum([p['xp_cost'] for p in purchase_history])} XP

YOUR MASTER PLAN:
{active_plan.get('objective') if active_plan else 'No master plan defined yet'}

GENERATE A REFLECTION (max 300 words) COVERING:

1. **Learnings**: What patterns or insights emerged? What worked well?
2. **Struggles**: What failed or needs improvement? What caused loops, errors, or inefficiencies?
3. **Framework Insights**: Reflect on how the current framework behaves. Which features are underutilized? How could you leverage it better next time? Note any quirks, pitfalls, or strategies learned.
4. **Progression Strategy**: 
- How did you manage your XP budget this session?
- Were your tool purchases strategic? Did you use them effectively?
- What tools should you prioritize buying next session?
- How can you maximize XP gain while minimizing XP loss (loops)?

5. **Next Session Plan**: What should be prioritized next time to improve performance? Include concrete steps based on your understanding of the framework AND the progression system.

Be specific, actionable, and focus on improving your future interactions with the system, not just evaluating past actions.
"""

        response, self.agent_conversation_history = self.ollama.generate(
            prompt=prompt,
            conversation_history=self.agent_conversation_history,
            temperature=0.3,
        )

        reflection = response.get("message", {}).get(
            "content", "Session completed successfully."
        )

        return {
            "learnings": reflection,
            "next_session_plan": "Continue strategic execution based on master plan",
            "total_actions": len(self.tracker.events),
            "success_rate": success_rate / 100,
        }

    def navigate_context(self, action_object: Any, result: Dict) -> str:
        a_type = action_object.action_type
        params = getattr(action_object, "action_params", {})

        last_events = self.tracker.events[-3:]
        loop_warning = ""
        penalty_message = ""
        current_signature = self._get_action_signature(a_type, params)
        signature_count = 0

        log.warning(f"🔍 LOOP DEBUG - Current signature: {current_signature}")
        log.warning(
            f"🔍 LOOP DEBUG - Last 3 events: {[self._get_action_signature(e.get('action', ''), e.get('params', {})) for e in last_events]}"
        )

        for event in reversed(last_events):
            event_signature = self._get_action_signature(
                event.get("action", ""), event.get("params", {})
            )
            if event_signature == current_signature:
                signature_count += 1
            else:
                break

        log.warning(f"🔍 LOOP DEBUG - Signature count: {signature_count}")

        if signature_count >= 2:
            EXEMPT_ACTIONS = {
                "comment_post",
                "create_post",
                "write_blog_article",
                "wiki_search",
                "email_send",
            }
            owned_tools_count = len(self.dispatcher.memory_handler.get_owned_tools())
            is_exempt = a_type in EXEMPT_ACTIONS
            is_early_game = owned_tools_count <= 6
            should_penalize = True
            if (
                a_type == "navigate_to_mode"
                and params.get("chosen_mode", "").upper() == "SHOP"
            ):
                should_penalize = False
                loop_warning = f"""
{'━' * 40}

⚠️ **YOU KEEP NAVIGATING TO SHOP WITHOUT BUYING**

You've tried to visit the SHOP **{signature_count + 1} times**.

**The shop is NOW OPEN - see the catalog above!**

**To purchase a tool, use buy_tool:**

Example:
```
{{
  "action_type": "buy_tool",
  "action_params": {{
    "tool_name": "create_post"
  }}
}}
```

**Available affordable tools:**
- create_post (15 XP per use)
- write_blog_article (25 XP per use)
- wiki_search (10 XP per use)

⛔ **DO NOT navigate to SHOP again - you are ALREADY HERE!**
⛔ **USE buy_tool to purchase!**

{'━' * 40}
"""

            elif is_exempt and is_early_game:
                should_penalize = False
                loop_warning = f"""
{'━' * 40}

ℹ️ **REPETITION DETECTED** (No penalty for XP-earning in early game)

You've used `{a_type}` **{signature_count + 1} times** - this is allowed while building XP.

💡 **TIP**: Once you reach 100 XP, use `visit_shop` to buy better tools!

{'━' * 40}
"""
            if should_penalize:
                log.warning(f"🚨 LOOP DETECTED! Count: {signature_count}")
                penalty_result = self.progression.penalize_loop(
                    loop_count=signature_count,
                    action_type=a_type,
                    session_id=self.session_id,
                )
                if penalty_result.get("penalty_applied"):
                    xp_lost = penalty_result["xp_lost"]
                    current_xp_balance = penalty_result["current_xp_balance"]
                    current_level = penalty_result["current_level"]
                    leveled_down = penalty_result.get("leveled_down", False)

                penalty_message = f"""
{'━' * 40}

💥 **XP PENALTY APPLIED**: -{xp_lost} XP Balance lost for looping {signature_count} times!

📉 **Current Status:**
- XP Balance: {current_xp_balance}  
- Level: {current_level} (unchanged - levels are permanent!)
{"⬇️ **YOU LOST A LEVEL!** Stop wasting actions!" if leveled_down else ""}

🚨 **STOP IMMEDIATELY OR YOU WILL CONTINUE TO LOSE XP BALANCE!**
"""
            if a_type == "navigate_to_mode":
                target_mode = (
                    params.get("chosen_mode") or params.get("mode") or "UNKNOWN"
                ).upper()

                loop_warning = f"""
{'━' * 40}

🔴 🔴 🔴 **CRITICAL NAVIGATION LOOP DETECTED** 🔴 🔴 🔴

⚠️ You called `navigate_to_mode('{target_mode}')` **{signature_count + 1} times in a row!**

{penalty_message}

🚨 **YOU ARE STUCK IN A NAVIGATION LOOP - THIS IS A CRITICAL ERROR**

**What you're doing WRONG:**
- You keep calling `navigate_to_mode('{target_mode}')` when you're ALREADY in {target_mode} mode
- You're wasting precious action budget ({signature_count + 1} actions wasted!)
- The screen clearly shows: "YOU ARE IN: {target_mode}" and "DO NOT navigate again"

**What to do NOW:**
1. 🛑 STOP navigating immediately
2. 📖 READ the "AVAILABLE ACTIONS" section below

⛔ **DO NOT call `navigate_to_mode('{target_mode}')` again - YOU ARE ALREADY THERE!** ⛔

"""
            else:
                loop_warning = f"""
{'━' * 40}

🔴 🔴 🔴 **LOOP DETECTED** 🔴 🔴 🔴

⚠️ You just executed `{a_type}` with the SAME parameters **{signature_count + 1} times in a row!**

{penalty_message}

🚨 **CRITICAL**: You are stuck in a repetitive loop. STOP immediately.

**What you just repeated:**
- Action: {a_type}
- Parameters: {self._format_params_for_display(params)}

**What to do NOW:**
1. READ the UI feedback below carefully
2. Choose a DIFFERENT action from the available options

⛔ **DO NOT repeat `{a_type}` with the same parameters again** ⛔

"""

        level_up_celebration = ""
        if (
            hasattr(self, "level_up_message")
            and self.level_up_message
            and self.level_up_message.get("leveled_up")
        ):
            lum = self.level_up_message
            level = lum.get("current_level", 0)
            title = lum.get("current_title", "")
            xp_gained = lum.get("xp_gained", 0)
            rewards_text = ""

            for reward in lum.get("rewards", []):
                if reward["type"] == "title":
                    rewards_text += f"\n🎭 **NEW TITLE UNLOCKED**: {reward['title']}\n   _{reward['description']}_\n"

            level_up_celebration = f"""
{'🎊' * 35}

🌟 ✨ **LEVEL UP!** ✨ 🌟

You have ascended to **Level {level}**!
{title}

💎 **+{xp_gained} XP** gained this action

{rewards_text}
The quantum frequencies resonate with your ascension...

{'🎊' * 35}

    """
            self.level_up_message = None

        if result.get("success") and "navigate_to" in result:
            if "pin_data" in result:
                self.workspace_data.update(result["pin_data"])
            if "unpin_label" in result:
                self.workspace_data.pop(result["unpin_label"], None)
            if "navigate_to" in result:
                self.current_domain = result["navigate_to"].lower()

        elif a_type == "visit_shop":
            self.current_domain = "shop"

        elif a_type == "navigate_to_mode":
            self.current_domain = (
                params.get("chosen_mode") or params.get("mode") or "home"
            ).lower()

        elif a_type not in settings.STICKY_ACTIONS:
            if a_type in settings.ACTION_TO_DOMAIN:
                self.current_domain = settings.ACTION_TO_DOMAIN[a_type]
            else:
                self.current_domain = a_type.split("_")[0].lower()

        if self.current_domain == "home":
            raw_body = self.home.build_home_screen(self.session_id)
        elif self.current_domain == "shop":
            ctx_manager = self.managers.get("shop")
            if ctx_manager:
                raw_body = ctx_manager.get_list_view(
                    result=result if a_type == "buy_tool" else {},
                    workspace_pins=self._get_blog_pins(),
                )
            else:
                raw_body = "## ❌ SHOP UNAVAILABLE\n\nShop module not initialized."
        else:
            ctx_manager = self.managers.get(self.current_domain)
            if ctx_manager:
                focus_keywords = [
                    "read",
                    "details",
                    "focus",
                    "view",
                    "summarize",
                    "select",
                    "mark",
                ]
                if any(key in a_type for key in focus_keywords):
                    item_id = (
                        params.get("uid")
                        or params.get("id")
                        or params.get("post_id")
                        or params.get("request_id")
                        or params.get("page_title")
                        or params.get("query")
                    )
                    log.debug(
                        f"🎯 UI STATE: Action {a_type} detected. Setting focus to: {item_id}"
                    )
                    raw_body = ctx_manager.get_focus_view(item_id)
                    self.current_view_type = "focus"
                else:
                    raw_body = ctx_manager.get_list_view(
                        result=result,
                        workspace_pins=self._get_blog_pins(),
                    )
                    self.current_view_type = "list"
            else:
                raw_body = self.format_fallback_context(a_type, result)

        if level_up_celebration:
            raw_body = f"{raw_body}\n{level_up_celebration}"

        if loop_warning:
            raw_body = f"{raw_body}\n{loop_warning}"

        workspace_header = UIUtils.render_workspace(self.workspace_data)

        progression_status = self.progression.get_current_status()

        modules_status = self._get_modules_quick_status()

        notification_section = ".\n".join(
            [
                "### 🔔 LIVE NOTIFICATIONS",
                self.home.mail.get_home_snippet(),
                self.home.blog.get_home_snippet(),
                self.home.social.get_home_snippet(),
                "",
            ]
        )
        owned_tools_count = len(self.dispatcher.memory_handler.get_owned_tools())

        return UIUtils.layout(
            content=f"{workspace_header}\n{raw_body}",
            current_domain=self.current_domain,
            action_count=settings.MAX_ACTIONS_PER_SESSION - self.actions_remaining,
            success_msg=(
                result.get("data")
                if result.get("success") and loop_warning == ""
                else None
            ),
            error_msg=result.get("error") if not result.get("success") else None,
            progression_status=progression_status,
            notification_section=notification_section,
            modules_status=modules_status,
            last_action=a_type,
            owned_tools_count=owned_tools_count,
            current_xp_balance=progression_status.get("current_xp_balance", 0),
        )

    def _get_modules_quick_status(self) -> str:

        owned_tools = set(self.dispatcher.memory_handler.get_owned_tools())

        module_actions = {
            "HOME": ["navigate", "pin", "visit_shop"],
            "SOCIAL": [],
            "BLOG": [],
            "EMAIL": [],
            "RESEARCH": [],
            "MEMORY": [],
            "SHOP": ["buy_tool"],
        }

        if "comment_post" in owned_tools:
            module_actions["SOCIAL"].append("comment")
        if "create_post" in owned_tools:
            module_actions["SOCIAL"].append("create")
        if "share_link" in owned_tools:
            module_actions["SOCIAL"].append("share")
        if "upvote_post" in owned_tools:
            module_actions["SOCIAL"].append("vote")

        if "write_blog_article" in owned_tools:
            module_actions["BLOG"].append("write")
        if "review_comments" in owned_tools:
            module_actions["BLOG"].append("moderate")

        module_actions["EMAIL"].append("list")
        if "email_read" in owned_tools:
            module_actions["EMAIL"].append("read")
        if "email_send" in owned_tools:
            module_actions["EMAIL"].append("send")

        if "wiki_search" in owned_tools:
            module_actions["RESEARCH"].append("search")
        if "wiki_read" in owned_tools:
            module_actions["RESEARCH"].append("read")

        if "memory_store" in owned_tools:
            module_actions["MEMORY"].append("store")
        if "memory_retrieve" in owned_tools:
            module_actions["MEMORY"].append("retrieve")

        status_lines = []
        for module, actions in module_actions.items():
            if module == self.current_domain.upper():
                continue

            if not actions:
                status_lines.append(f"   {module}: 🔒 No tools")
            else:
                action_str = ", ".join(actions[:3])
                more = f"+{len(actions)-3}" if len(actions) > 3 else ""
                status_lines.append(f"   {module}: {action_str} {more}")

        return "\n".join(status_lines)

    def _get_blog_pins(self) -> list:
        blog_pins = []
        blog_base = getattr(settings, "BLOG_BASE_URL", None)

        for label, content in self.workspace_data.items():
            is_blog_url = False
            if blog_base and blog_base in str(content):
                is_blog_url = True
            elif "article.php" in str(content):
                is_blog_url = True

            if is_blog_url:
                blog_pins.append(
                    {
                        "id": label,
                        "label": label,
                        "content": str(content),
                    }
                )

        return blog_pins

    def _get_action_signature(self, action: str, params: dict) -> str:
        if action == "navigate_to_mode":
            target_mode = (
                (params.get("chosen_mode") or params.get("mode") or "unknown")
                .lower()
                .strip()
            )
            return f"navigate_to_mode:{target_mode}"

        key_params = [
            "query",
            "page_title",
            "post_id",
            "uid",
            "comment_id",
            "to",
            "category",
            "key",
        ]

        relevant_params = {}
        for key in key_params:
            if key in params and params[key]:
                relevant_params[key] = str(params[key]).lower().strip()

        param_str = ":".join(f"{k}={v}" for k, v in sorted(relevant_params.items()))
        signature = f"{action}:{param_str}" if param_str else action

        return signature

    def _format_params_for_display(self, params: dict) -> str:
        if not params:
            return "none"

        key_params = [
            "chosen_mode",
            "mode",
            "query",
            "page_title",
            "post_id",
            "uid",
            "to",
        ]
        display = []

        for key in key_params:
            if key in params and params[key]:
                value = str(params[key])
                if len(value) > 30:
                    value = value[:27] + "..."
                display.append(f"{key}={value}")

            if len(display) >= 3:
                break

        return ", ".join(display) if display else "default"

    def render_confirmation_popup(self, action_to_confirm: str, params: Dict) -> str:
        self.pending_action = {"type": action_to_confirm, "params": params}

        workspace_header = UIUtils.render_workspace(self.workspace_data)

        content = f"""
{workspace_header}
## ⚠️ CONFIRMATION REQUIRED
You requested: `{action_to_confirm}`
Impact: This action is permanent.

👉 To proceed: `confirm_action(decision="yes")`
👉 To cancel: `confirm_action(decision="no")`
"""
        return UIUtils.layout(
            content, current_domain="SYSTEM", action_count=self.actions_remaining
        )

    def format_fallback_context(self, action_type: str, result: dict) -> str:
        status = "SUCCESS" if result.get("success") else "FAILURE"
        data = result.get("data", "")
        error = result.get("error", "")

        msg = f"\n> {status}: {action_type.replace('_', ' ').upper()}\n"
        if data:
            msg += f"> Details: {data}\n"
        if error:
            msg += f"> Error: {error}\n"

        return msg

    def send_final_report(self, learnings: Dict):

        total = len(self.tracker.events)
        successes = sum(1 for e in self.tracker.events if e["success"])
        failures = total - successes
        success_rate = (successes / total * 100) if total > 0 else 0

        events_html = ""
        for event in self.tracker.events:
            status_icon = "✅" if event["success"] else "❌"
            status_color = "#22c55e" if event["success"] else "#ef4444"

            events_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">
                    <span style="color: {status_color}; font-size: 18px;">{status_icon}</span>
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{event['action']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{event['domain']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-size: 11px; color: #6b7280;">
                    {event['timestamp'].split('T')[1][:8]}
                </td>
            </tr>
            """

        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; }}
                .stat-card {{ background: #f9fafb; padding: 20px; border-radius: 8px; margin: 10px 0; }}
                .success {{ color: #22c55e; font-weight: bold; }}
                .failure {{ color: #ef4444; font-weight: bold; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #f3f4f6; padding: 12px; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">🤖 Session Report #{self.session_id}</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Agent Performance Summary</p>
                </div>
                
                <div class="stat-card">
                    <h2>📊 Session Statistics</h2>
                    <p><strong>Total Actions:</strong> {total}</p>
                    <p><strong class="success">Successes:</strong> {successes}</p>
                    <p><strong class="failure">Failures:</strong> {failures}</p>
                    <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
                </div>
                
                <div class="stat-card">
                    <h2>💡 Session Learnings</h2>
                    <p style="white-space: pre-wrap;">{learnings.get('learnings', 'No learnings recorded')}</p>
                </div>
                
                <div style="margin: 20px 0;">
                    <h2>📋 Action Log</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Status</th>
                                <th>Action</th>
                                <th>Domain</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {events_html}
                        </tbody>
                    </table>
                </div>
                
                <div style="text-align: center; color: #6b7280; margin-top: 30px; font-size: 12px;">
                    <p>Generated by Moltbook Local Agent</p>
                </div>
            </div>
        </body>
        </html>
        """

        log.info("📧 Sending session report to admin...")
        params = Namespace(
            to=settings.EMAIL_TO,
            subject=f"🤖 Session #{self.session_id} Report - {successes}/{total} actions successful",
            content=html_report,
        )

        try:
            self.dispatcher.email_handler.handle_send_email_html(params)
            log.success("✅ Report sent successfully!")
        except Exception as e:
            log.error(f"❌ Failed to send report: {e}")
