from typing import Type, Union, get_args, Any, Literal, Annotated
from pydantic import BaseModel, Field, create_model
from src.screens.home import HomeScreen
from src.screens.social import MoltbookScreen
from src.screens.blog import BlogScreen
from src.screens.email import EmailScreen
from src.screens.master_plan import StrategyScreen, StrictPlanScreen
from src.screens.wikipedia import ResearchScreen
from src.screens.global_actions import ConfirmAction, RefreshHomeAction
from src.settings import AvailableModule
from src.utils import log
from src.screens.base import BaseAction


class SchemaFactory:
    @staticmethod
    def get_schema_for_context(domain: str, is_popup_active: bool) -> Type[BaseModel]:

        if is_popup_active:

            class ConfirmLock(BaseModel):
                action: Union[ConfirmAction, RefreshHomeAction]

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
        }

        base_schema = screens.get(target, HomeScreen)

        if target in ["blog", "email", "mail", "social", "research", "wikipedia"]:
            return SchemaFactory._restrict_navigation(
                base_schema, current_domain=target
            )

        return base_schema

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
