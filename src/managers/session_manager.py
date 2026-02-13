from typing import Dict, Any
from argparse import Namespace
from src.utils import log
from src.utils.ui_utils import UIUtils
from src.screens.factory import SchemaFactory
from src.settings import settings


class SessionManager:
    def __init__(
        self,
        home_manager,
        managers_map,
        dispatcher,
        ollama_provider,
        tracker,
        email_reporter,
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
        self.tracker = tracker
        self.email_reporter = email_reporter

    def start_session(self):
        self.session_id = self.home.memory.create_session()
        log.info(
            f"🚀 Session {self.session_id} started. Budget: {self.actions_remaining}"
        )

        initial_body = self.home.build_home_screen(self.session_id)

        self.current_context = UIUtils.layout(
            content=initial_body,
            current_domain="home",
            action_count=0,
        )

        self.run_loop()

    def run_loop(self):
        while self.actions_remaining > 0:
            has_plan = self.dispatcher.plan_handler.has_active_plan()

            if not has_plan:
                log.warning("⚠️ System Locked: Waiting for Master Plan...")
                self.current_domain = "plan"

                current_schema = SchemaFactory.get_schema_for_context(
                    domain="plan", is_popup_active=False
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
                current_schema = SchemaFactory.get_schema_for_context(
                    domain=self.current_domain,
                    is_popup_active=bool(self.pending_action),
                )

            action_object = self.ollama.get_next_action(
                self.current_context,
                self.actions_remaining,
                schema=current_schema,
                agent_name=settings.AGENT_NAME,
            )

            if not action_object or action_object.action_type == "session_finish":
                log.success("🏁 Session finished by agent.")
                break

            result = self.dispatcher.execute(action_object)

            self.tracker.log_event(
                domain=self.current_domain,
                action_type=getattr(action_object, "action_type", "unknown"),
                result=result,
            )

            if self.current_domain == "finish":
                break

            if "pin_data" in result:
                self.workspace_data.update(result["pin_data"])
            if "unpin_label" in result:
                label_to_remove = result["unpin_label"]
                self.workspace_data.pop(label_to_remove, None)

            self.actions_remaining -= 1

            self.current_context = self.navigate_context(action_object, result)
            log.info(f"📉 Actions left: {self.actions_remaining}")

        log.success("🏁 Session limit reached.")

        session_learnings = self._generate_session_learnings()

        self.home.memory.archive_session(
            session_id=self.session_id,
            summary=session_learnings,
            history=self.ollama.conversation_history,
            actions=[e["action"] for e in self.tracker.events],
        )

        self.send_final_report(session_learnings)

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

        prompt = f"""
Analyze this AI agent session and provide a concise reflection.

SESSION STATISTICS:
- Total actions: {len(self.tracker.events)}
- Successes: {successes}
- Failures: {failures}
- Success rate: {success_rate:.1f}%

ACTIONS LOG:
{events_summary}

GENERATE A REFLECTION (max 200 words):

1. **Learnings**: What patterns or insights emerged? What worked well?

2. **Struggles**: What failed or needs improvement? What caused loops or errors?

3. **Next Session Plan**: What should be prioritized next time to improve performance?

Be specific and actionable. Focus on behavior patterns, not individual actions.
"""

        response = self.ollama.generate(
            prompt=prompt, save_to_history=False, temperature=0.3
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

        current_signature = self._get_action_signature(a_type, params)

        signature_count = 0
        for event in reversed(last_events):
            event_signature = self._get_action_signature(
                event.get("action", ""), event.get("params", {})
            )
            if event_signature == current_signature:
                signature_count += 1
            else:
                break

        if signature_count >= 2:
            loop_warning = f"""
🔴 🔴 🔴 **LOOP DETECTED** 🔴 🔴 🔴

⚠️ You just executed `{a_type}` with the SAME parameters **{signature_count} times in a row!**

🚨 **CRITICAL**: You are stuck in a repetitive loop. STOP immediately.

**What you just repeated:**
- Action: {a_type}
- Parameters: {self._format_params_for_display(params)}

**What to do NOW:**
1. READ the UI feedback below carefully
2. Choose a DIFFERENT action from the available options
3. If you're stuck or nothing to do here, use `refresh_home` to go to another module

⛔ **DO NOT repeat `{a_type}` with the same parameters again** ⛔

{'━' * 70}

"""

        if result.get("success") and "navigate_to" in result:
            if "pin_data" in result:
                self.workspace_data.update(result["pin_data"])
            if "unpin_label" in result:
                self.workspace_data.pop(result["unpin_label"], None)
            if "navigate_to" in result:
                self.current_domain = result["navigate_to"].lower()

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
                else:
                    raw_body = ctx_manager.get_list_view(result=result)
            else:
                raw_body = self.format_fallback_context(a_type, result)

        if loop_warning:
            raw_body = f"{loop_warning}\n{raw_body}"

        workspace_header = UIUtils.render_workspace(self.workspace_data)

        return UIUtils.layout(
            content=f"{workspace_header}\n{raw_body}",
            current_domain=self.current_domain,
            action_count=settings.MAX_ACTIONS_PER_SESSION - self.actions_remaining,
            success_msg=result.get("data") if result.get("success") else None,
            error_msg=result.get("error") if not result.get("success") else None,
        )

    def _get_action_signature(self, action: str, params: dict) -> str:
        key_params = [
            "chosen_mode",
            "mode",
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
                    <p><strong>🎮 XP:</strong> {self.tracker.xp} | <strong>Level:</strong> {self.tracker.level}</p>
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
