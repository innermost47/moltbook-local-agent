from pydantic import BaseModel, Field
from typing import Literal
from src.screens.base import BaseAction


class BuyToolAction(BaseAction):
    action_type: Literal["buy_tool"] = "buy_tool"
    action_params: "BuyToolParams"


class BuyToolParams(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to purchase")
    reasoning: str = Field(..., description="Why you want this tool")


class BuyArtifactAction(BaseAction):
    action_type: Literal["buy_artifact"] = "buy_artifact"
    action_params: "BuyArtifactParams"


class BuyArtifactParams(BaseModel):
    artifact_name: str = Field(..., description="Name of the artifact")
    reasoning: str = Field(..., description="Expected benefit")


class VisitShopAction(BaseAction):
    action_type: Literal["visit_shop"] = "visit_shop"
    action_params: "VisitShopParams"


class VisitShopParams(BaseModel):
    pass
