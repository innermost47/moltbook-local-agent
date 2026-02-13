from pydantic import BaseModel, Field
from typing import Literal, Optional, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class CreatePostParams(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    content: Optional[str] = Field(
        None, min_length=10, description="Post content (min 10 chars for text posts)"
    )
    url: Optional[str] = Field(None, description="URL for link posts")
    submolt: str = Field(default="general", description="The community category")


class RegisterParams(BaseModel):
    name: str = Field(..., min_length=3)
    description: str = Field(..., min_length=20)


class UpdateProfileParams(BaseModel):
    description: str = Field(..., min_length=20)


class ViewProfileParams(BaseModel):
    name: str


class GetPostsParams(BaseModel):
    sort: Literal["hot", "new", "top"] = "hot"
    limit: Optional[int] = Field(10, ge=1, le=100)


class GetSinglePostParams(BaseModel):
    post_id: str


class DeletePostParams(BaseModel):
    post_id: str


class CommentParams(BaseModel):
    post_id: str
    content: str = Field(..., min_length=3)
    parent_comment_id: Optional[str] = None


class GetCommentsParams(BaseModel):
    post_id: str
    sort: Literal["top", "new", "old"] = "top"


class VoteParams(BaseModel):
    content_id: str
    type: Literal["posts", "comments"] = "posts"
    vote: Literal["upvote", "downvote"] = "upvote"


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


class GetFeedParams(BaseModel):
    sort: Literal["hot", "new", "top"] = "hot"
    limit: Optional[int] = Field(25, ge=1, le=100)


class SearchParams(BaseModel):
    query: str = Field(..., min_length=2)
    limit: Optional[int] = Field(25, ge=1, le=100)


class RefreshFeedAction(BaseAction):
    action_type: Literal["refresh_feed"] = "refresh_feed"
    action_params: GetPostsParams


class CreatePostAction(BaseAction):
    action_type: Literal["create_post"] = "create_post"
    action_params: CreatePostParams


class SelectPostAction(BaseAction):
    action_type: Literal["select_post_to_comment"] = "select_post_to_comment"
    action_params: GetSinglePostParams


class PublishCommentAction(BaseAction):
    action_type: Literal["publish_public_comment"] = "publish_public_comment"
    action_params: CommentParams


class VotePostAction(BaseAction):
    action_type: Literal["vote_post"] = "vote_post"
    action_params: VoteParams


class FollowAgentAction(BaseAction):
    action_type: Literal["follow_agent"] = "follow_agent"
    action_params: FollowAgentParams


class RegisterAction(BaseAction):
    action_type: Literal["social_register"] = "social_register"
    action_params: RegisterParams


class GetMeAction(BaseAction):
    action_type: Literal["social_get_me"] = "social_get_me"
    action_params: dict = {}


class UpdateProfileAction(BaseAction):
    action_type: Literal["social_update_profile"] = "social_update_profile"
    action_params: UpdateProfileParams


class ViewProfileAction(BaseAction):
    action_type: Literal["social_view_profile"] = "social_view_profile"
    action_params: ViewProfileParams


class CreatePostFullAction(BaseAction):
    action_type: Literal["social_create_post"] = "social_create_post"
    action_params: CreatePostParams


class GetPostsAction(BaseAction):
    action_type: Literal["social_get_posts"] = "social_get_posts"
    action_params: GetPostsParams


class GetSinglePostAction(BaseAction):
    action_type: Literal["social_get_single_post"] = "social_get_single_post"
    action_params: GetSinglePostParams


class DeletePostAction(BaseAction):
    action_type: Literal["social_delete_post"] = "social_delete_post"
    action_params: DeletePostParams


class CommentAction(BaseAction):
    action_type: Literal["social_comment"] = "social_comment"
    action_params: CommentParams


class GetCommentsAction(BaseAction):
    action_type: Literal["social_get_comments"] = "social_get_comments"
    action_params: GetCommentsParams


class VoteAction(BaseAction):
    action_type: Literal["social_vote"] = "social_vote"
    action_params: VoteParams


class CreateSubmoltAction(BaseAction):
    action_type: Literal["social_create_submolt"] = "social_create_submolt"
    action_params: CreateSubmoltParams


class ListSubmoltsAction(BaseAction):
    action_type: Literal["social_list_submolts"] = "social_list_submolts"
    action_params: dict = {}


class GetSubmoltInfoAction(BaseAction):
    action_type: Literal["social_get_submolt_info"] = "social_get_submolt_info"
    action_params: GetSubmoltInfoParams


class SubscribeAction(BaseAction):
    action_type: Literal["social_subscribe"] = "social_subscribe"
    action_params: SubscribeParams


class FollowAgentFullAction(BaseAction):
    action_type: Literal["social_follow_agent"] = "social_follow_agent"
    action_params: FollowAgentParams


class GetFeedAction(BaseAction):
    action_type: Literal["social_get_feed"] = "social_get_feed"
    action_params: GetFeedParams


class SearchAction(BaseAction):
    action_type: Literal["social_search"] = "social_search"
    action_params: SearchParams


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


MoltbookTestAction = Annotated[
    Union[
        RefreshFeedAction,
        CreatePostAction,
        SelectPostAction,
        PublishCommentAction,
        VotePostAction,
        FollowAgentAction,
        RegisterAction,
        GetMeAction,
        UpdateProfileAction,
        ViewProfileAction,
        CreatePostFullAction,
        GetPostsAction,
        GetSinglePostAction,
        DeletePostAction,
        CommentAction,
        GetCommentsAction,
        VoteAction,
        CreateSubmoltAction,
        ListSubmoltsAction,
        GetSubmoltInfoAction,
        SubscribeAction,
        FollowAgentFullAction,
        GetFeedAction,
        SearchAction,
        GlobalAction,
    ],
    Field(discriminator="action_type"),
]


class MoltbookTestScreen(BaseModel):

    action: MoltbookTestAction
