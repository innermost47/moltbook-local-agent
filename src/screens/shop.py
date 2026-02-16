from pydantic import BaseModel, Field
from typing import Union, Literal, Annotated
from src.screens.base import BaseAction
from src.screens.global_actions import GlobalAction


class BuyToolParams(BaseModel):
    tool_name: str = Field(
        ..., description="Exact name of the tool to purchase from shop catalog"
    )
    reasoning: str = Field(
        default="", description="Why you want to buy this tool (optional)"
    )


class BuyToolAction(BaseAction):
    action_type: Literal["buy_tool"] = "buy_tool"
    action_params: BuyToolParams


ShopPossibleActions = Annotated[
    Union[
        GlobalAction,
        BuyToolAction,
    ],
    Field(discriminator="action_type"),
]


class ShopScreen(BaseModel):
    action: ShopPossibleActions
