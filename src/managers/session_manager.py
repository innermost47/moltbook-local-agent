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
        self.send_final_report()

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

    def send_final_report(self):
        report_text = self.tracker.get_session_report()
        log.info("📧 Sending session report to admin...")
        params = Namespace(
            to=settings.EMAIL_TO,
            subject=f"Session Report - XP: {self.tracker.xp}",
            content=report_text,
        )
        self.dispatcher.email_handler.handle_send_email(params)
