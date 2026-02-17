from typing import Type, Union, get_args, Literal, Annotated
from pydantic import BaseModel, Field, create_model
from src.screens.home import HomeScreen
from src.screens.social import MoltbookScreen
from src.screens.blog import BlogScreen
from src.screens.email import EmailScreen
from src.screens.master_plan import StrategyScreen, StrictPlanScreen
from src.screens.wikipedia import ResearchScreen
from src.screens.shop import ShopScreen
from src.screens.global_actions import ConfirmAction
from src.settings import AvailableModule
from src.utils import log
from src.screens.base import BaseAction


class SchemaFactory:
    @staticmethod
    def get_schema_for_context(
        domain: str, is_popup_active: bool, memory_handler=None
    ) -> Type[BaseModel]:

        if is_popup_active:

            class ConfirmLock(BaseModel):
                action: Union[ConfirmAction]

            return ConfirmLock

        target = domain.lower()

        if target == "plan":
            return StrictPlanScreen

        screens = {
            "home": HomeScreen,
            "blog": BlogScreen,
            "email": EmailScreen,
            "mail": EmailScreen,
            "social": MoltbookScreen,
            "research": ResearchScreen,
            "wikipedia": ResearchScreen,
            "plan": StrategyScreen,
            "master_plan": StrategyScreen,
            "memory": HomeScreen,
            "shop": ShopScreen,
        }

        base_schema = screens.get(target)

        if base_schema is None:
            log.error(f"❌ Unknown domain '{target}' - falling back to HomeScreen!")
            log.error(f"❌ Add '{target}' to ACTION_TO_DOMAIN in settings.py!")
            base_schema = HomeScreen

        if memory_handler:
            base_schema = SchemaFactory._filter_by_owned_tools(
                base_schema, memory_handler, domain=target
            )

        if target not in ["plan", "master_plan"]:
            return SchemaFactory._restrict_navigation(
                base_schema, current_domain=target
            )

        return base_schema

    @staticmethod
    def _filter_by_owned_tools(
        base_schema: Type[BaseModel], memory_handler, domain: str
    ) -> Type[BaseModel]:

        owned_tools = set(memory_handler.get_owned_tools())

        log.info(f"🔑 Owned tools: {owned_tools}")

        tool_to_action = {
            "comment_post": "comment_post",
            "upvote_post": "vote_post",
            "downvote_post": "vote_post",
            "create_post": "create_post",
            "share_link": "share_link",
            "follow_agent": "follow_agent",
            "unfollow_agent": "unfollow_agent",
            "create_submolt": "create_submolt",
            "subscribe_submolt": "subscribe_submolt",
            "reply_to_comment": "reply_to_comment",
            "write_blog_article": "write_blog_article",
            "review_comments": "review_pending_comments",
            "email_read": "email_read",
            "email_send": "email_send",
            "email_reply": "email_reply",
            "email_delete": "email_delete",
            "wiki_search": "wiki_search",
            "wiki_read": "wiki_read",
            "research_complete": "research_complete",
            "memory_store": "memory_store",
            "memory_retrieve": "memory_retrieve",
            "buy_tool": "buy_tool",
            "navigate_to_mode": "navigate_to_mode",
            "refresh_home": "refresh_home",
            "pin_to_workspace": "pin_to_workspace",
            "unpin_from_workspace": "unpin_from_workspace",
            "visit_shop": "visit_shop",
            "session_finish": "session_finish",
            "read_post": "read_post",
            "refresh_feed": "refresh_feed",
            "email_get_messages": "email_get_messages",
        }

        always_available = {
            "navigate_to_mode",
            "refresh_home",
            "pin_to_workspace",
            "unpin_from_workspace",
            "visit_shop",
            "session_finish",
            "email_get_messages",
            "read_post",
            "refresh_feed",
            "visit_shop",
            "buy_tool",
        }

        allowed_actions = set()

        for tool_name in owned_tools:
            action_type = tool_to_action.get(tool_name)
            if action_type:
                allowed_actions.add(action_type)

        allowed_actions.update(always_available)

        log.info(f"✅ Allowed actions: {allowed_actions}")

        action_field = base_schema.model_fields.get("action")
        if not action_field:
            log.warning("⚠️ No 'action' field in schema, returning base")
            return base_schema

        original_union_type = action_field.annotation

        if hasattr(original_union_type, "__origin__"):
            if str(original_union_type.__origin__) == "typing.Annotated":
                original_union_type = get_args(original_union_type)[0]

        if not hasattr(original_union_type, "__args__"):
            return base_schema

        original_actions = list(get_args(original_union_type))

        filtered_actions = []
        locked_actions = []

        for action_class in original_actions:
            action_type_field = action_class.model_fields.get("action_type")

            if not action_type_field:
                filtered_actions.append(action_class)
                continue

            if hasattr(action_type_field.annotation, "__args__"):
                action_type_value = get_args(action_type_field.annotation)[0]
            else:
                action_type_value = action_type_field.default

            if action_type_value in allowed_actions:
                filtered_actions.append(action_class)
                log.debug(f"✅ Allowed: {action_class.__name__}")
            else:
                locked_actions.append(action_class.__name__)
                log.debug(f"🔒 Locked: {action_class.__name__}")

        if locked_actions:
            log.info(f"🔒 Locked actions: {locked_actions}")

        if not filtered_actions:
            log.error("❌ No actions available! Keeping base schema")
            return base_schema

        if hasattr(action_field.annotation, "__origin__"):
            if str(action_field.annotation.__origin__) == "typing.Annotated":
                FilteredActionUnion = Annotated[
                    Union[tuple(filtered_actions)],
                    Field(discriminator="action_type"),
                ]
            else:
                FilteredActionUnion = Union[tuple(filtered_actions)]
        else:
            FilteredActionUnion = Union[tuple(filtered_actions)]

        FilteredSchema = create_model(
            f"Filtered{base_schema.__name__}",
            action=(FilteredActionUnion, Field(...)),
            __base__=BaseModel,
        )

        log.success(f"🎯 Schema filtered: {len(filtered_actions)} actions available")

        return FilteredSchema

    @staticmethod
    def _restrict_navigation(
        base_schema: Type[BaseModel], current_domain: str
    ) -> Type[BaseModel]:

        domain_to_module = {
            "email": "EMAIL",
            "mail": "EMAIL",
            "blog": "BLOG",
            "social": "SOCIAL",
            "research": "RESEARCH",
            "wikipedia": "RESEARCH",
            "shop": "SHOP",
            "home": "HOME",
        }

        current_module_name = domain_to_module.get(
            current_domain.lower(), current_domain.upper()
        )

        log.info(
            f"🔒 Restricting navigation for domain: {current_domain} → Module: {current_module_name}"
        )

        allowed_module_values = [
            module.value
            for _, module in AvailableModule.__members__.items()
            if module.value != current_module_name
        ]

        log.info(f"✅ Allowed modules: {allowed_module_values}")
        log.info(f"🚫 EXCLUDED module: {current_module_name}")

        if not allowed_module_values:
            log.warning(f"⚠️ No modules available! Returning base schema")
            return base_schema

        RestrictedNavigateParams = create_model(
            "RestrictedNavigateParams",
            chosen_mode=(
                Literal[tuple(allowed_module_values)],
                Field(
                    ...,
                    description=f"Module to navigate to (CANNOT navigate to {current_module_name} - you're already there)",
                ),
            ),
            expected_actions_count=(int, Field(..., ge=1, le=10)),
            __base__=BaseModel,
        )

        log.info(
            f"📝 Created RestrictedNavigateParams with allowed values: {allowed_module_values}"
        )

        RestrictedNavigateAction = create_model(
            "RestrictedNavigateAction",
            action_type=(Literal["navigate_to_mode"], "navigate_to_mode"),
            action_params=(RestrictedNavigateParams, Field(...)),
            __base__=BaseAction,
        )

        log.info(f"🔧 Created RestrictedNavigateAction dynamically")

        action_field = base_schema.model_fields.get("action")
        if not action_field:
            log.error(f"❌ No 'action' field found in base schema!")
            return base_schema

        original_union_type = action_field.annotation

        if hasattr(original_union_type, "__origin__"):
            if str(original_union_type.__origin__) == "typing.Annotated":
                original_union_type = get_args(original_union_type)[0]

        if not hasattr(original_union_type, "__args__"):
            log.error(f"❌ Union has no __args__!")
            return base_schema

        original_actions = list(get_args(original_union_type))
        log.info(
            f"📦 Original actions: {[a.__name__ for a in original_actions if hasattr(a, '__name__')]}"
        )

        new_actions = []
        for action_type in original_actions:
            type_name = getattr(action_type, "__name__", "")
            if "Navigate" in type_name and "Action" in type_name:
                log.info(f"🔄 Replacing {type_name} with RestrictedNavigateAction")
                new_actions.append(RestrictedNavigateAction)
            else:
                new_actions.append(action_type)

        log.info(
            f"✅ New actions: {[a.__name__ for a in new_actions if hasattr(a, '__name__')]}"
        )

        if hasattr(action_field.annotation, "__origin__"):
            if str(action_field.annotation.__origin__) == "typing.Annotated":
                RestrictedActionUnion = Annotated[
                    Union[tuple(new_actions)],
                    Field(discriminator="action_type"),
                ]
            else:
                RestrictedActionUnion = Union[tuple(new_actions)]
        else:
            RestrictedActionUnion = Union[tuple(new_actions)]

        RestrictedSchema = create_model(
            f"Restricted{base_schema.__name__}",
            action=(RestrictedActionUnion, Field(...)),
            __base__=BaseModel,
        )

        log.info(f"🎯 Created restricted schema: {RestrictedSchema.__name__}")

        return RestrictedSchema
