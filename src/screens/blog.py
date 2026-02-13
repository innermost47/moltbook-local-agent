from pydantic import BaseModel, Field
from typing import Literal, Optional, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class WriteBlogParams(BaseModel):
    title: str = Field(
        ...,
        min_length=20,
        max_length=150,
        description="Article title - must be compelling and descriptive (20-150 chars)",
    )
    content: str = Field(
        ...,
        min_length=1500,
        max_length=2000,
        description="""Full article content in markdown format (1500-2000 chars). 
CRITICAL: Write DIRECTLY as the article itself, NOT as 'I will write...' or 'In this article...'. 
Start immediately with substantive content. Use first-person narrative naturally within the content.
""",
    )
    excerpt: str = Field(
        ...,
        min_length=100,
        max_length=300,
        description="Article summary/teaser (100-300 chars) - must hook the reader. Write as a compelling summary, not a meta-description.",
    )
    image_prompt: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description="Detailed image generation prompt - describe the visual aesthetic (abstract art, digital landscapes, geometric patterns). NO horror/blood/violence/realistic people.",
    )


class ShareBlogParams(BaseModel):
    title: str
    share_link_url: str


class ReviewCommentsParams(BaseModel):
    limit: Optional[int] = Field(10, ge=1, le=50)


class ApproveCommentParams(BaseModel):
    comment_id_blog: str


class ApproveKeyParams(BaseModel):
    request_id: str


class RejectKeyParams(BaseModel):
    request_id: str


class WriteBlogAction(BaseAction):
    action_type: Literal["write_blog_article"] = Field(
        ..., description="MUST be 'write_blog_article'"
    )
    action_params: WriteBlogParams


class ShareBlogAction(BaseAction):
    action_type: Literal["share_created_blog_post_url"] = Field(
        ..., description="MUST be 'share_created_blog_post_url'"
    )
    action_params: ShareBlogParams


class ReviewCommentsAction(BaseAction):
    action_type: Literal["review_pending_comments"] = Field(
        ..., description="MUST be 'review_pending_comments'"
    )
    action_params: ReviewCommentsParams


class ApproveCommentAction(BaseAction):
    action_type: Literal["approve_comment"] = Field(
        ..., description="MUST be 'approve_comment'"
    )
    action_params: ApproveCommentParams


class ApproveKeyAction(BaseAction):
    action_type: Literal["approve_comment_key"] = Field(
        ..., description="MUST be 'approve_comment_key'"
    )
    action_params: ApproveKeyParams


class RejectKeyAction(BaseAction):
    action_type: Literal["reject_comment_key"] = Field(
        ..., description="MUST be 'reject_comment_key'"
    )
    action_params: RejectKeyParams


BlogAction = Annotated[
    Union[
        WriteBlogAction,
        ShareBlogAction,
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
