from typing import Type, Union
from pydantic import BaseModel

from src.screens.home import HomeScreen
from src.screens.social import MoltbookScreen
from src.screens.blog import BlogScreen
from src.screens.email import EmailScreen
from src.screens.master_plan import StrategyScreen, StrictPlanScreen
from src.screens.wikipedia import ResearchScreen
from src.screens.global_actions import ConfirmAction, RefreshHomeAction


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

        selected = screens.get(target, HomeScreen)

        return selected
