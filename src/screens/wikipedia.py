from pydantic import BaseModel, Field
from typing import List, Literal, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class WikiSearchParams(BaseModel):
    query: str = Field(
        ..., description="The optimized English search query for Wikipedia"
    )


class WikiReadParams(BaseModel):
    page_title: str = Field(
        ..., description="The exact title of the Wikipedia page to read"
    )


class ResearchSummaryParams(BaseModel):
    objective: str = Field(..., description="The original research goal")
    findings: List[str] = Field(
        ..., min_items=1, description="List of key facts extracted"
    )
    is_objective_met: bool = Field(
        ..., description="Whether the research goal is fully achieved"
    )


class WikiSearchAction(BaseAction):
    action_type: Literal["wiki_search"] = Field(
        ...,
        description="STEP 1: Use this to discover relevant Wikipedia articles. DO NOT use search twice for the same topic.",
    )
    action_params: WikiSearchParams


class WikiReadAction(BaseAction):
    action_type: Literal["wiki_read"] = Field(
        ...,
        description="STEP 2: Use this to extract facts from a specific page discovered via search. Reading is MANDATORY to fulfill research goals.",
    )
    action_params: WikiReadParams


class ResearchCompletionAction(BaseAction):
    action_type: Literal["research_complete"] = Field(
        ...,
        description="STEP 3: Finalize and save findings. Use this only after you have extracted enough facts via 'wiki_read'.",
    )
    action_params: ResearchSummaryParams


ResearchAction = Annotated[
    Union[WikiSearchAction, WikiReadAction, ResearchCompletionAction, GlobalAction],
    Field(discriminator="action_type"),
]


class ResearchScreen(BaseModel):
    action: ResearchAction = Field(
        ...,
        description="Current Research Phase. Follow the cycle: Search -> Read -> Complete. Don't waste energy points on redundant searches.",
    )
