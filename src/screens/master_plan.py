from pydantic import BaseModel, Field
from typing import List, Literal, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class InitializePlanParams(BaseModel):
    objective: str = Field(..., description="Long-term goal")
    strategy: str = Field(..., description="High-level approach")
    milestones: List[str] = Field(..., min_length=3, description="Major steps")


class UpdatePlanParams(BaseModel):
    should_update: bool = Field(..., description="Update master plan?")
    new_objective: str = Field(..., description="Refined objective")
    new_strategy: str = Field(..., description="Refined strategy")
    new_milestones: List[str] = Field(
        ..., min_length=1, description="Updated milestones"
    )


class InitializeMasterPlan(BaseAction):
    action_type: Literal["plan_initialize"] = "plan_initialize"
    action_params: InitializePlanParams


class UpdateMasterPlan(BaseAction):
    action_type: Literal["plan_update"] = "plan_update"
    action_params: UpdatePlanParams


StrategyAction = Annotated[
    Union[InitializeMasterPlan, UpdateMasterPlan, GlobalAction],
    Field(discriminator="action_type"),
]


class StrategyScreen(BaseModel):
    action: StrategyAction


class StrictPlanScreen(BaseModel):
    action: InitializeMasterPlan
