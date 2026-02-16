from typing import Type, get_args, List, Dict, Any
from src.screens.global_actions import (
    MemoryStoreAction,
    MemoryRetrieveAction,
    PinAction,
    UnpinAction,
    SessionFinishAction,
)
from src.settings import AvailableModule
from src.utils import log
from src.screens.base import BaseAction


class ToolFactory:

    @staticmethod
    def action_to_tool(action_class: Type[BaseAction]) -> dict:
        try:
            action_type_field = action_class.model_fields.get("action_type")
            if not action_type_field:
                log.error(f"❌ No action_type in {action_class.__name__}")
                return None

            action_name = action_type_field.default

            params_field = action_class.model_fields.get("action_params")
            if not params_field:
                log.error(f"❌ No action_params in {action_class.__name__}")
                return None

            params_annotation = params_field.annotation

            origin = getattr(params_annotation, "__origin__", None)
            if origin is dict or params_annotation is dict:
                params_schema = {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": True,
                }

            elif hasattr(params_annotation, "model_json_schema"):
                params_schema = params_annotation.model_json_schema()

                if "$defs" in params_schema:
                    params_schema.pop("$defs", None)
            else:
                log.error(
                    f"❌ Unknown params type for {action_class.__name__}: {params_annotation}"
                )
                return None

            tool = {
                "type": "function",
                "function": {
                    "name": action_name,
                    "description": f"Execute {action_name}",
                    "parameters": params_schema,
                },
            }

            log.debug(f"✅ Created tool: {action_name}")
            return tool

        except Exception as e:
            log.error(f"❌ Error converting {action_class.__name__} to tool: {e}")
            return None

    @staticmethod
    def get_tools_for_domain(
        domain: str,
        include_globals: bool = True,
        allow_navigation: bool = True,
        allow_memory: bool = True,
        memory_handler=None,
    ) -> List[dict]:

        tools = []
        target = domain.lower()

        if memory_handler:
            owned_tools = set(memory_handler.get_owned_tools())
            log.info(f"🔑 Filtering tools based on ownership: {owned_tools}")
        else:
            owned_tools = None

        domain_actions = ToolFactory._get_domain_actions(target)

        for action_class in domain_actions:
            if owned_tools is not None:
                action_type_field = action_class.model_fields.get("action_type")
                if action_type_field:
                    action_name = action_type_field.default

                    tool_to_action = {
                        "comment_post": "comment_post",
                        "create_post": "create_post",
                        "share_link": "share_link",
                        "vote_post": "vote_post",
                        "write_blog_article": "write_blog_article",
                        "review_comments": "review_pending_comments",
                        "email_read": "email_read",
                        "email_send": "email_send",
                        "email_delete": "email_delete",
                        "wiki_search": "wiki_search",
                        "wiki_read": "wiki_read",
                        "research_complete": "research_complete",
                        "memory_store": "memory_store",
                        "memory_retrieve": "memory_retrieve",
                    }

                    always_available = {
                        "navigate_to_mode",
                        "refresh_home",
                        "pin_to_workspace",
                        "unpin_from_workspace",
                        "session_finish",
                        "email_get_messages",
                        "read_post",
                        "refresh_feed",
                    }

                    if action_name not in always_available:
                        tool_name = None
                        for t, a in tool_to_action.items():
                            if a == action_name:
                                tool_name = t
                                break

                        if tool_name and tool_name not in owned_tools:
                            log.debug(f"🔒 Skipping {action_name} (tool not owned)")
                            continue

            tool = ToolFactory.action_to_tool(action_class)
            if tool:
                tools.append(tool)

        if include_globals:
            global_tools = ToolFactory._get_global_tools(
                current_domain=target,
                allow_navigation=allow_navigation,
                allow_memory=allow_memory,
                memory_handler=memory_handler,
            )
            tools.extend(global_tools)

        log.info(f"🔧 Generated {len(tools)} tools for domain '{domain}'")
        return tools

    @staticmethod
    def _get_domain_actions(domain: str) -> List[Type[BaseAction]]:
        from src.screens.blog import WriteBlogAction, ReviewCommentsAction
        from src.screens.email import (
            EmailListAction,
            EmailReadAction,
            EmailSendAction,
            EmailDeleteAction,
        )
        from src.screens.social import (
            CreatePostAction,
            CommentPostAction,
            VotePostAction,
            ShareLinkAction,
        )
        from src.screens.wikipedia import (
            WikiSearchAction,
            WikiReadAction,
            ResearchCompletionAction,
        )
        from src.screens.master_plan import InitializeMasterPlan, UpdateMasterPlan

        actions_map = {
            "blog": [WriteBlogAction, ReviewCommentsAction],
            "email": [
                EmailListAction,
                EmailReadAction,
                EmailSendAction,
                EmailDeleteAction,
            ],
            "mail": [
                EmailListAction,
                EmailReadAction,
                EmailSendAction,
                EmailDeleteAction,
            ],
            "social": [
                CreatePostAction,
                CommentPostAction,
                VotePostAction,
                ShareLinkAction,
            ],
            "research": [WikiSearchAction, WikiReadAction, ResearchCompletionAction],
            "wikipedia": [WikiSearchAction, WikiReadAction, ResearchCompletionAction],
            "plan": [InitializeMasterPlan, UpdateMasterPlan],
            "master_plan": [InitializeMasterPlan, UpdateMasterPlan],
            "home": [],
        }

        return actions_map.get(domain, [])

    @staticmethod
    def _get_global_tools(
        current_domain: str,
        allow_navigation: bool = True,
        allow_memory: bool = True,
        memory_handler=None,
    ) -> List[dict]:
        tools = []

        if allow_navigation:
            nav_tool = ToolFactory._create_restricted_navigation_tool(current_domain)
            if nav_tool:
                tools.append(nav_tool)

        if allow_memory and memory_handler:
            owned_tools = set(memory_handler.get_owned_tools())

            if "memory_store" in owned_tools:
                mem_store = ToolFactory.action_to_tool(MemoryStoreAction)
                if mem_store:
                    tools.append(mem_store)

            if "memory_retrieve" in owned_tools:
                mem_retrieve = ToolFactory.action_to_tool(MemoryRetrieveAction)
                if mem_retrieve:
                    tools.append(mem_retrieve)

        elif allow_memory and not memory_handler:
            mem_store = ToolFactory.action_to_tool(MemoryStoreAction)
            mem_retrieve = ToolFactory.action_to_tool(MemoryRetrieveAction)
            if mem_store:
                tools.append(mem_store)
            if mem_retrieve:
                tools.append(mem_retrieve)

        pin_tool = ToolFactory.action_to_tool(PinAction)
        unpin_tool = ToolFactory.action_to_tool(UnpinAction)
        if pin_tool:
            tools.append(pin_tool)
        if unpin_tool:
            tools.append(unpin_tool)

        finish_tool = ToolFactory.action_to_tool(SessionFinishAction)
        if finish_tool:
            tools.append(finish_tool)

        return tools

    @staticmethod
    def _create_restricted_navigation_tool(current_domain: str) -> dict:
        domain_to_module = {
            "email": "EMAIL",
            "mail": "EMAIL",
            "blog": "BLOG",
            "social": "SOCIAL",
            "research": "RESEARCH",
            "wikipedia": "RESEARCH",
            "home": "HOME",
        }

        current_module = domain_to_module.get(
            current_domain.lower(), current_domain.upper()
        )

        allowed_modules = [
            module.value for module in AvailableModule if module.value != current_module
        ]

        if not allowed_modules:
            log.warning(f"⚠️ No navigation modules available for {current_domain}")
            return None

        return {
            "type": "function",
            "function": {
                "name": "navigate_to_mode",
                "description": f"Navigate to a different module (current: {current_module})",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chosen_mode": {
                            "type": "string",
                            "enum": allowed_modules,
                            "description": f"Module to navigate to (cannot go to {current_module})",
                        },
                        "expected_actions_count": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Number of actions expected in target module",
                        },
                    },
                    "required": ["chosen_mode", "expected_actions_count"],
                },
            },
        }
