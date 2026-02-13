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

        self.send_final_report()

    def _generate_session_learnings(self) -> Dict:

        events_summary = "\n".join(
            [
                f"{'✅' if e['success'] else '❌'} {e['action']} in {e['domain']}"
                for e in self.tracker.events
            ]
        )

        prompt = f"""
Analyze this session and provide a concise reflection:

{events_summary}

Generate:
1. **Learnings**: 2-3 key insights or patterns discovered
2. **Struggles**: What didn't work or needs improvement
3. **Next Session Plan**: Recommended priorities for next time

Keep it brief (max 200 words total).
"""

        response = self.ollama.client.chat(
            model=self.ollama.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3, "num_predict": 300},
        )

        reflection = response["message"]["content"]

        return {
            "learnings": reflection,
            "next_session_plan": "Continue strategic execution based on master plan",
            "total_actions": len(self.tracker.events),
            "success_rate": (
                sum(1 for e in self.tracker.events if e["success"])
                / len(self.tracker.events)
                if self.tracker.events
                else 0
            ),
        }

    def navigate_context(self, action_object: Any, result: Dict) -> str:
        a_type = action_object.action_type
        params = getattr(action_object, "action_params", {})

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

        workspace_header = UIUtils.render_workspace(self.workspace_data)

        return UIUtils.layout(
            content=f"{workspace_header}\n{raw_body}",
            current_domain=self.current_domain,
            action_count=settings.MAX_ACTIONS_PER_SESSION - self.actions_remaining,
            success_msg=result.get("data") if result.get("success") else None,
            error_msg=result.get("error") if not result.get("success") else None,
        )

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
            self.dispatcher.email_handler.handle_send_email(params)
            log.success("✅ Report sent successfully!")
        except Exception as e:
            log.error(f"❌ Failed to send report: {e}")
