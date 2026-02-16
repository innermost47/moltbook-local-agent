from pydantic import BaseModel, Field
from typing import List, Literal, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class WikiSearchParams(BaseModel):
    query: str = Field(..., description="Wikipedia search query")


class WikiReadParams(BaseModel):
    page_title: str = Field(..., description="Wikipedia page title")


class ResearchSummaryParams(BaseModel):
    objective: str = Field(..., description="Research goal")
    findings: List[str] = Field(..., min_items=1, description="Key facts")
    is_objective_met: bool = Field(..., description="Goal achieved?")


class WikiSearchAction(BaseAction):
    action_type: Literal["wiki_search"] = "wiki_search"
    action_params: WikiSearchParams


class WikiReadAction(BaseAction):
    action_type: Literal["wiki_read"] = "wiki_read"
    action_params: WikiReadParams


class ResearchCompletionAction(BaseAction):
    action_type: Literal["research_complete"] = "research_complete"
    action_params: ResearchSummaryParams


ResearchAction = Annotated[
    Union[WikiSearchAction, WikiReadAction, ResearchCompletionAction, GlobalAction],
    Field(discriminator="action_type"),
]


class ResearchScreen(BaseModel):
    action: ResearchAction
