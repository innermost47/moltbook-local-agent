from pydantic import BaseModel, Field
from typing import Literal, Optional, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class ReadPostParams(BaseModel):
    post_id: str = Field(..., description="Post ID")


class ReadPostAction(BaseAction):
    action_type: Literal["read_post"] = "read_post"
    action_params: ReadPostParams


class CommentPostParams(BaseModel):
    post_id: str = Field(..., description="Post ID")
    content: str = Field(..., min_length=3, description="Comment text (min 3 chars)")


class CommentPostAction(BaseAction):
    action_type: Literal["comment_post"] = "comment_post"
    action_params: CommentPostParams


class ReplyToCommentParams(BaseModel):
    post_id: str = Field(..., description="Post ID")
    parent_comment_id: str = Field(..., description="Comment ID to reply to")
    content: str = Field(..., min_length=3, description="Reply text (min 3 chars)")


class ReplyToCommentAction(BaseAction):
    action_type: Literal["reply_to_comment"] = "reply_to_comment"
    action_params: ReplyToCommentParams


class VotePostParams(BaseModel):
    post_id: str = Field(..., description="Post ID")
    vote_type: Literal["upvote", "downvote"] = Field(
        ..., description="upvote or downvote"
    )


class VotePostAction(BaseAction):
    action_type: Literal["vote_post"] = "vote_post"
    action_params: VotePostParams


class CreatePostParams(BaseModel):
    title: str = Field(
        ..., min_length=5, max_length=200, description="Title (5-200 chars)"
    )
    content: str = Field(..., min_length=10, description="Content (min 10 chars)")
    submolt: str = Field(default="general", description="Category (default: general)")


class CreatePostAction(BaseAction):
    action_type: Literal["create_post"] = "create_post"
    action_params: CreatePostParams


class ShareLinkParams(BaseModel):
    title: str = Field(..., min_length=5, max_length=200, description="Link title")
    url_to_share: str = Field(..., description="URL (http:// or https://)")
    submolt: str = Field(default="general", description="Category (default: general)")


class ShareLinkAction(BaseAction):
    action_type: Literal["share_link"] = "share_link"
    action_params: ShareLinkParams


class RefreshFeedParams(BaseModel):
    pass


class RefreshFeedAction(BaseAction):
    action_type: Literal["refresh_feed"] = "refresh_feed"
    action_params: RefreshFeedParams = Field(default_factory=dict)


SimplifiedMoltbookAction = Annotated[
    Union[
        ReadPostAction,
        CommentPostAction,
        ReplyToCommentAction,
        VotePostAction,
        CreatePostAction,
        ShareLinkAction,
        RefreshFeedAction,
        GlobalAction,
    ],
    Field(discriminator="action_type"),
]


class SimplifiedMoltbookScreen(BaseModel):

    action: SimplifiedMoltbookAction


class RegisterParams(BaseModel):
    name: str = Field(..., min_length=3)
    description: str = Field(..., min_length=20)


class UpdateProfileParams(BaseModel):
    description: str = Field(..., min_length=20)


class ViewProfileParams(BaseModel):
    name: str


class CreateSubmoltParams(BaseModel):
    name: str = Field(..., min_length=3)
    display_name: str
    description: str = Field(..., min_length=20)


class GetSubmoltInfoParams(BaseModel):
    submolt_name: str


class SubscribeParams(BaseModel):
    submolt_name: str
    action: Literal["subscribe", "unsubscribe"] = "subscribe"


class FollowAgentParams(BaseModel):
    agent_name: str
    action: Literal["follow", "unfollow"] = "follow"


class SearchParams(BaseModel):
    query: str = Field(..., min_length=2)
    limit: Optional[int] = Field(25, ge=1, le=100)


class DeletePostParams(BaseModel):
    post_id: str


class RegisterAction(BaseAction):
    action_type: Literal["social_register"] = "social_register"
    action_params: RegisterParams


class GetMeAction(BaseAction):
    action_type: Literal["social_get_me"] = "social_get_me"
    action_params: dict = Field(default_factory=dict)


class UpdateProfileAction(BaseAction):
    action_type: Literal["social_update_profile"] = "social_update_profile"
    action_params: UpdateProfileParams


class ViewProfileAction(BaseAction):
    action_type: Literal["social_view_profile"] = "social_view_profile"
    action_params: ViewProfileParams


class DeletePostAction(BaseAction):
    action_type: Literal["social_delete_post"] = "social_delete_post"
    action_params: DeletePostParams


class CreateSubmoltAction(BaseAction):
    action_type: Literal["social_create_submolt"] = "social_create_submolt"
    action_params: CreateSubmoltParams


class ListSubmoltsAction(BaseAction):
    action_type: Literal["social_list_submolts"] = "social_list_submolts"
    action_params: dict = Field(default_factory=dict)


class GetSubmoltInfoAction(BaseAction):
    action_type: Literal["social_get_submolt_info"] = "social_get_submolt_info"
    action_params: GetSubmoltInfoParams


class SubscribeAction(BaseAction):
    action_type: Literal["social_subscribe"] = "social_subscribe"
    action_params: SubscribeParams


class FollowAgentAction(BaseAction):
    action_type: Literal["social_follow_agent"] = "social_follow_agent"
    action_params: FollowAgentParams


class SearchAction(BaseAction):
    action_type: Literal["social_search"] = "social_search"
    action_params: SearchParams


FullMoltbookAction = Annotated[
    Union[
        ReadPostAction,
        CommentPostAction,
        ReplyToCommentAction,
        VotePostAction,
        CreatePostAction,
        ShareLinkAction,
        RefreshFeedAction,
        RegisterAction,
        GetMeAction,
        UpdateProfileAction,
        ViewProfileAction,
        DeletePostAction,
        CreateSubmoltAction,
        ListSubmoltsAction,
        GetSubmoltInfoAction,
        SubscribeAction,
        FollowAgentAction,
        SearchAction,
        GlobalAction,
    ],
    Field(discriminator="action_type"),
]


class FullMoltbookScreen(BaseModel):

    action: FullMoltbookAction


MoltbookAction = SimplifiedMoltbookAction
MoltbookScreen = SimplifiedMoltbookScreen

MoltbookTestAction = FullMoltbookAction
MoltbookTestScreen = FullMoltbookScreen
