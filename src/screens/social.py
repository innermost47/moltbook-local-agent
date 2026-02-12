from pydantic import BaseModel, Field
from typing import Literal, Optional, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class CreatePostParams(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=50, description="Post content (min 50 chars)")
    submolt: str = Field(
        ..., description="The community category (e.g., 'tech', 'general')"
    )


class SelectPostParams(BaseModel):
    post_id: str = Field(
        ..., description="ID of the post to select for viewing or interacting"
    )


class SelectCommentParams(BaseModel):
    post_id: str
    comment_id: str


class PublishCommentParams(BaseModel):
    post_id: str
    content: str = Field(
        ..., min_length=10, description="Comment content (min 10 chars)"
    )


class ReplyCommentParams(BaseModel):
    post_id: str
    comment_id: str
    content: str = Field(..., min_length=10, description="Reply content (min 10 chars)")


class VotePostParams(BaseModel):
    post_id: str
    vote_type: Literal["upvote", "downvote"]


class FollowAgentParams(BaseModel):
    agent_name: str
    follow_type: Literal["follow", "unfollow"]


class RefreshFeedParams(BaseModel):
    sort: Literal["hot", "new", "top"] = "hot"
    limit: Optional[int] = Field(10, ge=1, le=25)


class RefreshFeedAction(BaseAction):
    action_type: Literal["refresh_feed"] = Field(
        ..., description="MUST be 'refresh_feed'"
    )
    action_params: RefreshFeedParams


class CreatePostAction(BaseAction):
    action_type: Literal["create_post"] = Field(
        ..., description="MUST be 'create_post'"
    )
    action_params: CreatePostParams


class SelectPostAction(BaseAction):
    action_type: Literal["select_post_to_comment"] = Field(
        ..., description="MUST be 'select_post_to_comment'"
    )
    action_params: SelectPostParams


class PublishCommentAction(BaseAction):
    action_type: Literal["publish_public_comment"] = Field(
        ..., description="MUST be 'publish_public_comment'"
    )
    action_params: PublishCommentParams


class VotePostAction(BaseAction):
    action_type: Literal["vote_post"] = Field(..., description="MUST be 'vote_post'")
    action_params: VotePostParams


class FollowAgentAction(BaseAction):
    action_type: Literal["follow_agent"] = Field(
        ..., description="MUST be 'follow_agent'"
    )
    action_params: FollowAgentParams


MoltbookAction = Annotated[
    Union[
        RefreshFeedAction,
        CreatePostAction,
        SelectPostAction,
        PublishCommentAction,
        VotePostAction,
        FollowAgentAction,
        GlobalAction,
    ],
    Field(discriminator="action_type"),
]


class MoltbookScreen(BaseModel):
    action: MoltbookAction
