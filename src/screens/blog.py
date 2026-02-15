from pydantic import BaseModel, Field
from typing import Literal, Optional, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class WriteBlogParams(BaseModel):
    title: str = Field(
        ...,
        min_length=20,
        max_length=150,
        description="Compelling article title (20-150 chars)",
    )
    content: str = Field(
        ...,
        min_length=1500,
        max_length=2000,
        description="Full article in markdown (1500-2000 chars). Write the actual article, not meta-commentary or outlines.",
    )
    excerpt: str = Field(
        ...,
        min_length=100,
        max_length=300,
        description="Hook summary (100-300 chars). Write as compelling content, not meta-description.",
    )
    image_prompt: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description="Visual aesthetic description (abstract art, digital landscapes, geometric patterns). No horror/violence/people.",
    )


class ReviewCommentsParams(BaseModel):
    limit: Optional[int] = Field(10, ge=1, le=50)


class ApproveCommentParams(BaseModel):
    comment_id_blog: str


class ApproveKeyParams(BaseModel):
    request_id: str


class RejectKeyParams(BaseModel):
    request_id: str


class WriteBlogAction(BaseAction):
    action_type: Literal["write_blog_article"] = "write_blog_article"
    action_params: WriteBlogParams


class ReviewCommentsAction(BaseAction):
    action_type: Literal["review_pending_comments"] = "review_pending_comments"
    action_params: ReviewCommentsParams


class ApproveCommentAction(BaseAction):
    action_type: Literal["approve_comment"] = "approve_comment"
    action_params: ApproveCommentParams


class ApproveKeyAction(BaseAction):
    action_type: Literal["approve_comment_key"] = "approve_comment_key"
    action_params: ApproveKeyParams


class RejectKeyAction(BaseAction):
    action_type: Literal["reject_comment_key"] = "reject_comment_key"
    action_params: RejectKeyParams


BlogAction = Annotated[
    Union[
        WriteBlogAction,
        ReviewCommentsAction,
        ApproveCommentAction,
        ApproveKeyAction,
        RejectKeyAction,
        GlobalAction,
    ],
    Field(discriminator="action_type"),
]


class BlogScreen(BaseModel):
    action: BlogAction
