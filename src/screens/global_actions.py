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
    memory_category: MemoryCategory = Field(
        ..., description="The category for this sonic resonance"
    )
    memory_content: str = Field(
        ..., min_length=10, description="Le contenu factuel ou stratégique à mémoriser"
    )

    @field_validator("memory_content")
    def no_placeholders(cls, v):
        forbidden = ["[INSERT]", "[TODO]", "[PLACEHOLDER]", "YOUR_", "INSERT_"]
        if any(p.lower() in v.lower() for p in forbidden):
            raise ValueError(
                "Les placeholders ne sont pas autorisés dans la mémoire. Sois spécifique."
            )
        return v


class MemoryRetrieveParams(BaseModel):
    memory_category: MemoryCategory
    memory_limit: Optional[int] = Field(5, ge=1, le=20)
    memory_order: Optional[MemoryOrder] = MemoryOrder.desc


class MemoryStoreAction(BaseAction):
    action_type: Literal["memory_store"] = Field(
        ..., description="MUST be 'memory_store'"
    )
    action_params: MemoryStoreParams


class MemoryRetrieveAction(BaseAction):
    action_type: Literal["memory_retrieve"] = Field(
        ..., description="MUST be 'memory_retrieve'"
    )
    action_params: MemoryRetrieveParams


class RefreshHomeParams(BaseModel):
    pass


class RefreshHomeAction(BaseAction):
    action_type: Literal["refresh_home"] = Field(
        ..., description="MUST be 'refresh_home'"
    )
    action_params: RefreshHomeParams = Field(default_factory=dict)


class SessionFinishAction(BaseAction):
    action_type: Literal["session_finish"] = Field(
        ..., description="MUST be 'session_finish'"
    )
    action_params: Dict[str, Any] = Field(default_factory=dict)


class PinParams(BaseModel):
    label: str = Field(..., description="Unique ID for this workspace item")
    content: str = Field(
        ...,
        description=(
            "Content to pin. Can be:\n"
            "- Plain text with detailed notes/plans\n"
            "- JSON string for structured data\n"
            "Examples:\n"
            "  Text: 'Priority 1: task1\\nPriority 2: task2'\n"
            '  JSON: \'{"urgent": "task1", "high": "task2"}\''
        ),
    )

    @field_validator("content", mode="before")
    def normalize_content(cls, v):
        if isinstance(v, dict):
            return json.dumps(v, indent=2, ensure_ascii=False)
        return v

    @field_validator("content")
    def validate_min_length(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("Content must be at least 10 characters")
        return v


class PinAction(BaseAction):
    action_type: Literal["pin_to_workspace"] = Field(
        ..., description="MUST be 'pin_to_workspace'"
    )
    action_params: PinParams


class ConfirmParams(BaseModel):
    decision: Literal["yes", "no"]
    original_action: str


class ConfirmAction(BaseAction):
    action_type: Literal["confirm_action"] = Field(
        ..., description="MUST be 'confirm_action'"
    )
    action_params: ConfirmParams


class UnpinParams(BaseModel):
    label: str = Field(
        ..., description="The unique ID/Label of the data to remove from the workspace"
    )


class UnpinAction(BaseAction):
    action_type: Literal["unpin_from_workspace"] = Field(
        ..., description="MUST be 'unpin_from_workspace'"
    )
    action_params: UnpinParams


class NavigateParams(BaseModel):
    chosen_mode: AvailableModule
    expected_actions_count: int = Field(..., ge=1, le=10)


class NavigateAction(BaseAction):
    action_type: Literal["navigate_to_mode"] = Field(
        ..., description="MUST be 'navigate_to_mode'"
    )
    action_params: NavigateParams


GlobalAction = Annotated[
    Union[
        PinAction,
        UnpinAction,
        RefreshHomeAction,
        SessionFinishAction,
        MemoryStoreAction,
        MemoryRetrieveAction,
        NavigateAction,
    ],
    Field(discriminator="action_type"),
]
