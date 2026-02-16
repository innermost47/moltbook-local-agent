import json
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, Union, Dict, Any, Annotated
from enum import Enum
from src.settings import MemoryCategory, AvailableModule
from src.screens.base import BaseAction


class MemoryOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class MemoryStoreParams(BaseModel):
    memory_category: MemoryCategory = Field(..., description="Memory category")
    memory_content: str = Field(..., min_length=10, description="Content to store")

    @field_validator("memory_content")
    def no_placeholders(cls, v):
        forbidden = ["[INSERT]", "[TODO]", "[PLACEHOLDER]", "YOUR_", "INSERT_"]
        if any(p.lower() in v.lower() for p in forbidden):
            raise ValueError("No placeholders allowed. Be specific.")
        return v


class MemoryRetrieveParams(BaseModel):
    memory_category: MemoryCategory
    memory_limit: Optional[int] = Field(5, ge=1, le=20)
    memory_order: Optional[MemoryOrder] = MemoryOrder.desc


class MemoryStoreAction(BaseAction):
    action_type: Literal["memory_store"] = "memory_store"
    action_params: MemoryStoreParams


class MemoryRetrieveAction(BaseAction):
    action_type: Literal["memory_retrieve"] = "memory_retrieve"
    action_params: MemoryRetrieveParams


class RefreshHomeParams(BaseModel):
    pass


class SessionFinishAction(BaseAction):
    action_type: Literal["session_finish"] = "session_finish"
    action_params: Dict[str, Any] = Field(default_factory=dict)


class PinParams(BaseModel):
    label: str = Field(..., description="Unique ID")
    content: str = Field(..., description="Text or JSON string to pin")

    @field_validator("content", mode="before")
    def normalize_content(cls, v):
        if isinstance(v, dict):
            return json.dumps(v, indent=2, ensure_ascii=False)
        return v

    @field_validator("content")
    def validate_min_length(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("Content min 10 chars")
        return v


class PinAction(BaseAction):
    action_type: Literal["pin_to_workspace"] = "pin_to_workspace"
    action_params: PinParams


class ConfirmParams(BaseModel):
    decision: Literal["yes", "no"]
    original_action: str


class ConfirmAction(BaseAction):
    action_type: Literal["confirm_action"] = "confirm_action"
    action_params: ConfirmParams


class UnpinParams(BaseModel):
    label: str = Field(..., description="ID to remove")


class UnpinAction(BaseAction):
    action_type: Literal["unpin_from_workspace"] = "unpin_from_workspace"
    action_params: UnpinParams


class NavigateParams(BaseModel):
    chosen_mode: AvailableModule
    expected_actions_count: int = Field(..., ge=1, le=10)


class NavigateAction(BaseAction):
    action_type: Literal["navigate_to_mode"] = "navigate_to_mode"
    action_params: NavigateParams


class VisitShopParams(BaseModel):
    pass


class VisitShopAction(BaseAction):
    action_type: Literal["visit_shop"] = "visit_shop"
    action_params: VisitShopParams


GlobalAction = Annotated[
    Union[
        PinAction,
        UnpinAction,
        SessionFinishAction,
        MemoryStoreAction,
        MemoryRetrieveAction,
        NavigateAction,
        VisitShopAction,
    ],
    Field(discriminator="action_type"),
]
