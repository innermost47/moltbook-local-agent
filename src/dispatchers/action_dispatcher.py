from typing import Any, Dict, Optional
from pydantic import BaseModel
from argparse import Namespace
import chromadb
from src.utils import log
from src.handlers.blog_handler import BlogHandler
from src.handlers.email_handler import EmailHandler
from src.handlers.social_handler import SocialHandler
from src.handlers.research_handler import ResearchHandler
from src.handlers.memory_handler import MemoryHandler
from src.handlers.plan_handler import PlanHandler
from src.handlers.shop_handler import ShopHandler
from src.settings import settings, AvailableModule
from src.utils.exceptions import (
    UnknownActionError,
    ActionPointExhausted,
    AgentException,
    SystemLogicError,
    get_exception_feedback,
)


class ActionDispatcher:
    def __init__(self, test_mode: bool = False, ollama=None):
        self.test_mode = test_mode
        chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
        collection = chroma_client.get_or_create_collection(name="knowledge")
        self.blog_handler = BlogHandler(test_mode)
        self.email_handler = EmailHandler(
            settings.AGENT_IMAP_SERVER,
            settings.AGENT_IMAP_SMTP_HOST,
            settings.AGENT_MAIL_BOX_EMAIL,
            settings.AGENT_MAIL_BOX_PASSWORD,
            test_mode,
        )
        self.research_handler = ResearchHandler(collection, test_mode)
        self.memory_handler = MemoryHandler(
            db_path=settings.DB_PATH, test_mode=test_mode
        )
        self.social_handler = SocialHandler(
            self.memory_handler, test_mode, ollama=ollama
        )
        self.plan_handler = PlanHandler(self.memory_handler)
        self.shop_handler = ShopHandler(
            memory_handler=self.memory_handler,
            progression_system=None,
        )

        self._handler_map = {
            "write_blog": self.blog_handler,
            "share_created": self.blog_handler,
            "approve_": self.blog_handler,
            "reject_": self.blog_handler,
            "review_": self.blog_handler,
            "email_": self.email_handler,
            "refresh_": self.social_handler,
            "create_post": self.social_handler,
            "select_": self.social_handler,
            "share_link": self.social_handler,
            "publish_": self.social_handler,
            "vote_": self.social_handler,
            "follow_": self.social_handler,
            "social_": self.social_handler,
            "wiki_": self.research_handler,
            "research_": self.research_handler,
            "memory_": self.memory_handler,
            "plan_": self.plan_handler,
            "buy_tool": self.shop_handler,
            "buy_artifact": self.shop_handler,
            "comment_post": self.social_handler,
            "reply_to_comment": self.social_handler,
            "read_post": self.social_handler,
        }

        self.session_manager = None

    def set_progression_system(self, progression_system):
        self.shop_handler.progression = progression_system

    def set_session_manager(self, session_manager):
        self.session_manager = session_manager

    def _extract_action_and_params(
        self, action_object: Any
    ) -> tuple[str | None, dict | None]:
        action_type = getattr(action_object, "action_type", None)

        if hasattr(action_object, "model_dump"):
            full_dump = action_object.model_dump()
        elif hasattr(action_object, "__dict__"):
            full_dump = vars(action_object)
        elif isinstance(action_object, dict):
            full_dump = action_object
        else:
            log.error(f"❌ Unrecognized action object type: {type(action_object)}")
            return action_type, None

        params = full_dump.get("action_params")

        if params is None:
            params = full_dump
        else:
            for key in ["reasoning", "self_criticism", "emotions"]:
                if key in full_dump and key not in params:
                    params[key] = full_dump[key]

        return action_type, params

    def _handle_builtin_actions(self, action_type: str, params: dict) -> dict:
        if action_type == "navigate_to_mode":
            return self.handle_navigation(params)

        if action_type == "pin_to_workspace":
            return self.handle_workspace_pin(params)

        if action_type == "unpin_from_workspace":
            return self.handle_workspace_unpin(params)

        if action_type == "confirm_action":
            return self.handle_confirm_action(params)

        if action_type == "refresh_home":
            return self.handle_refresh_home(params)

        return {}

    def execute(self, action_object: BaseModel) -> dict[str, Any]:
        action_type, params = self._extract_action_and_params(action_object)

        if not action_type or params is None:
            return {"success": False, "error": "Invalid action structure"}

        result = self._handle_builtin_actions(action_type, params)
        if result:
            return result

        handler = self._find_handler(action_type)
        if not handler:
            err = UnknownActionError(
                message=f"Action '{action_type}' is not recognized.",
                suggestion="Consult the available commands in the current UI context.",
            )
            feedback = get_exception_feedback(err)
            log.warning(f"⚠️ Unknown action attempted: {action_type}")
            return feedback

        if self.session_manager and self.session_manager.actions_remaining <= 0:
            err = ActionPointExhausted(
                message="No energy remaining.",
                suggestion="Use 'session_finish' to wrap up gracefully.",
            )
            feedback = get_exception_feedback(err)
            log.error("🔴 Energy depleted!")
            return feedback

        method_name = f"handle_{action_type}"
        handler_method = getattr(handler, method_name, None)
        if not handler_method:
            return {
                "success": False,
                "error": f"Method {method_name} not found in handler",
            }

        payload = (
            params.get("action_params", params) if isinstance(params, dict) else params
        )
        if isinstance(payload, dict):
            payload = Namespace(**payload)

        try:
            log.info(f"⚙️ Executing: {action_type}")
            result = handler_method(payload)

            return result

        except AgentException as e:
            feedback = get_exception_feedback(e)
            log.warning(f"⚠️ {e.__class__.__name__}: {e.message}")

            if self.session_manager and hasattr(self.session_manager, "tracker"):
                self.session_manager.tracker.apply_penalty(
                    exception_name=e.__class__.__name__,
                    xp_penalty=feedback.get("xp_penalty", 0),
                )

            return feedback

        except SystemLogicError as e:
            feedback = get_exception_feedback(e)
            log.error(f"💥 System Error: {e.details}")

            if self.session_manager:
                self.session_manager.actions_remaining += 1
                log.info("♻️ Energy refunded (system error)")

            return feedback

        except Exception as e:
            log.error(f"💥 Unexpected Error in {method_name}: {e}")
            feedback = get_exception_feedback(e)
            return feedback

    def handle_workspace_pin(self, params: Any) -> Dict:
        if isinstance(params, dict):
            label = params.get("label", "note")
            content = params.get("content", "")
        else:
            label = getattr(params, "label", "note")
            content = getattr(params, "content", "")

        if not content:
            log.warning(f"⚠️ Agent attempted to pin empty content to '{label}'")
            return {
                "success": False,
                "error": "Cannot pin an empty content. Provide 'content' to anchor the shard.",
            }

        log.success(f"📌 Workspace anchor set: {label}")

        return {
            "success": True,
            "data": f"Pinned: {label}",
            "pin_data": {label: content},
        }

    def handle_workspace_unpin(self, params: Any) -> Dict:
        if isinstance(params, dict):
            label = params.get("label", "")
        else:
            label = getattr(params, "label", "")

        if not label:
            return {"success": False, "error": "Specify the label to unpin."}

        return {
            "success": True,
            "data": f"Unpinned: {label}",
            "unpin_label": label,
        }

    def handle_confirm_action(self, params: Any) -> Dict:
        if isinstance(params, dict):
            decision = params.get("decision", "no")
        else:
            decision = getattr(params, "decision", "no")

        if decision.lower() != "yes":
            log.info("🚫 Agent chose NOT to proceed with the action.")
            if self.session_manager:
                self.session_manager.pending_action = None
            return {
                "success": True,
                "data": "Action cancelled.",
                "refresh_required": True,
            }

        if not self.session_manager or not self.session_manager.pending_action:
            return {
                "success": False,
                "error": "No pending action found to confirm.",
            }

        pending = self.session_manager.pending_action
        self.session_manager.pending_action = None

        original_params = pending["params"]

        if hasattr(original_params, "__dict__"):
            original_params.confirmed = True
        else:
            original_params["confirmed"] = True

        re_run_obj = Namespace(
            action_type=pending["type"], action_params=original_params
        )

        log.success(f"🔓 Confirmation received. Executing: {pending['type']}")
        return self.execute(re_run_obj)

    def _find_handler(self, action_type: str) -> Optional[Any]:
        for prefix, handler in self._handler_map.items():
            if action_type.startswith(prefix):
                return handler
        return None

    def handle_refresh_home(self, params: Any) -> Dict:
        if self.session_manager:
            self.session_manager.current_domain = "home"
            self.session_manager.pending_action = None
        return {"success": True, "data": "Navigated back to home dashboard."}

    def handle_navigation(self, action_object: Any) -> Dict:
        if isinstance(action_object, dict):
            params = action_object
        else:
            params = getattr(action_object, "__dict__", {})
            if not params.get("chosen_mode") and hasattr(
                action_object, "action_params"
            ):
                params = action_object.action_params

        chosen_mode = params.get("chosen_mode")

        if hasattr(chosen_mode, "value"):
            chosen_mode = chosen_mode.value

        if not chosen_mode:
            return {
                "success": False,
                "error": f"No mode specified. Expected 'chosen_mode', got keys: {list(params.keys())}",
            }

        if isinstance(chosen_mode, AvailableModule):
            module = chosen_mode
        else:
            try:
                module = AvailableModule(str(chosen_mode).upper())
            except ValueError:
                return {"success": False, "error": f"Invalid mode: {chosen_mode}"}

        new_domain = settings.MODULE_TO_DOMAIN.get(module)

        if new_domain and self.session_manager:
            self.session_manager.current_domain = new_domain
            log.success(f"Moving to {new_domain}")
            return {
                "success": True,
                "data": f"Successfully navigated to {module.value}.",
                "new_domain": new_domain,
            }

        return {
            "success": False,
            "error": f"No domain mapped or session unavailable for mode: {module.value}",
        }

    def handle_session_finish(self, params: Any) -> Dict:
        if self.session_manager:
            self.session_manager.actions_remaining = 0
            return {
                "success": True,
                "data": "Session finished by agent. Saving states...",
            }
        return {"success": False, "error": "Could not terminate session."}
