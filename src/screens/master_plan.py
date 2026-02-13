from pydantic import BaseModel, Field
from typing import List, Literal, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class InitializePlanParams(BaseModel):
    objective: str = Field(
        ...,
        description="The ultimate, long-term supreme goal of the agent. This is the core purpose.",
    )
    strategy: str = Field(
        ...,
        description="The high-level, permanent orchestration of modules to achieve the supreme goal.",
    )
    milestones: List[str] = Field(
        ...,
        min_length=3,
        description="The major sequential steps (pillars) toward the supreme goal.",
    )


class UpdatePlanParams(BaseModel):
    should_update: bool = Field(
        ...,
        description="Whether to evolve the permanent master plan based on deep session learnings.",
    )
    new_objective: str = Field(
        ...,
        description="The refined long-term objective (or current one if no change).",
    )
    new_strategy: str = Field(..., description="The refined long-term strategy.")
    new_milestones: List[str] = Field(
        ..., min_length=1, description="The updated list of major milestones."
    )


class InitializeMasterPlan(BaseAction):
    action_type: Literal["plan_initialize"] = Field(
        ...,
        description="Technical ID: 'plan_initialize'. Use this to define the agent's permanent mission.",
    )
    action_params: InitializePlanParams


class UpdateMasterPlan(BaseAction):
    action_type: Literal["plan_update"] = Field(
        ...,
        description="Technical ID: 'plan_update'. Use this to evolve the core trajectory.",
    )
    action_params: UpdatePlanParams


StrategyAction = Annotated[
    Union[InitializeMasterPlan, UpdateMasterPlan, GlobalAction],
    Field(discriminator="action_type"),
]


class StrategyScreen(BaseModel):
    action: StrategyAction = Field(
        ...,
        description="Neural Alignment Phase. Define or update the Master Plan to unlock the system's potential.",
    )


class StrictPlanScreen(BaseModel):
    action: InitializeMasterPlan = Field(..., description="MANDATORY: Initialize Plan.")
