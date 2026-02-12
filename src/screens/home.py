from pydantic import BaseModel, Field
from typing import Annotated
from src.screens.global_actions import GlobalAction


HomePossibleActions = Annotated[
    GlobalAction,
    Field(discriminator="action_type"),
]


class HomeScreen(BaseModel):
    action: HomePossibleActions
