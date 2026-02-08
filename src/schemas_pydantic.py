from pydantic import BaseModel, Field, field_validator
from typing import Union
from typing import Literal, Optional, List
from enum import Enum


class VoteType(str, Enum):
    upvote = "upvote"
    downvote = "downvote"
    none = "none"


class FollowType(str, Enum):
    follow = "follow"
    unfollow = "unfollow"
    none = "none"


class TodoStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"
    none = "none"


class MemoryCategory(str, Enum):
    interactions = "interactions"
    learnings = "learnings"
    strategies = "strategies"
    observations = "observations"
    goals = "goals"
    relationships = "relationships"
    experiments = "experiments"
    preferences = "preferences"
    failures = "failures"
    successes = "successes"
    ideas = "ideas"
    reflections = "reflections"


class MemoryOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class SelectPostParams(BaseModel):
    post_id: str = Field(..., description="ID of the post to select")


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


class CreatePostParams(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=50)
    submolt: str


class VotePostParams(BaseModel):
    post_id: str
    vote_type: VoteType


class FollowAgentParams(BaseModel):
    agent_name: str
    follow_type: FollowType


class RefreshFeedParams(BaseModel):
    sort: str
    limit: Optional[int] = 10


class WebScrapParams(BaseModel):
    web_domain: str
    web_query: str


class WebFetchParams(BaseModel):
    web_url: str


class ShareLinkParams(BaseModel):
    share_link_url: str
    content: str


class WriteBlogParams(BaseModel):
    title: str = Field(..., min_length=10, max_length=200)
    content: str = Field(
        ..., min_length=500, description="Full article content (min 500 chars)"
    )
    excerpt: str = Field(..., max_length=300)
    image_prompt: str

    class Config:
        extra = "forbid"


class ShareBlogParams(BaseModel):
    title: str
    share_link_url: str


class MemoryStoreParams(BaseModel):
    memory_category: MemoryCategory
    memory_content: str = Field(..., min_length=10)

    @field_validator("memory_content")
    def no_placeholders(cls, v):
        forbidden = ["[INSERT]", "[TODO]", "[PLACEHOLDER]", "YOUR_", "INSERT_"]
        if any(p.lower() in v.lower() for p in forbidden):
            raise ValueError("No placeholders allowed in memory_content")
        return v


class MemoryRetrieveParams(BaseModel):
    memory_category: MemoryCategory
    memory_limit: Optional[int] = 5
    memory_order: Optional[MemoryOrder] = MemoryOrder.desc


class UpdateTodoParams(BaseModel):
    todo_task: str
    todo_status: TodoStatus


class ApproveKeyParams(BaseModel):
    request_id: str


class RejectKeyParams(BaseModel):
    request_id: str


class ApproveCommentParams(BaseModel):
    comment_id_blog: str


class ReviewCommentsParams(BaseModel):
    limit: Optional[int] = 10


class SelectPostAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["select_post_to_comment"] = "select_post_to_comment"
    action_params: SelectPostParams


class SelectCommentAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["select_comment_to_reply"] = "select_comment_to_reply"
    action_params: SelectCommentParams


class PublishCommentAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["publish_public_comment"] = "publish_public_comment"
    action_params: PublishCommentParams


class ReplyCommentAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["reply_to_comment"] = "reply_to_comment"
    action_params: ReplyCommentParams


class CreatePostAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["create_post"] = "create_post"
    action_params: CreatePostParams


class VotePostAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["vote_post"] = "vote_post"
    action_params: VotePostParams


class FollowAgentAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["follow_agent"] = "follow_agent"
    action_params: FollowAgentParams


class RefreshFeedAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["refresh_feed"] = "refresh_feed"
    action_params: RefreshFeedParams


class WebScrapAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["web_scrap_for_links"] = "web_scrap_for_links"
    action_params: WebScrapParams


class WebFetchAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["web_fetch"] = "web_fetch"
    action_params: WebFetchParams


class ShareLinkAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["share_link"] = "share_link"
    action_params: ShareLinkParams


class WriteBlogAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["write_blog_article"] = "write_blog_article"
    action_params: WriteBlogParams


class ShareBlogAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["share_created_blog_post_url"] = "share_created_blog_post_url"
    action_params: ShareBlogParams


class MemoryStoreAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["memory_store"] = "memory_store"
    action_params: MemoryStoreParams


class MemoryRetrieveAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["memory_retrieve"] = "memory_retrieve"
    action_params: MemoryRetrieveParams


class UpdateTodoAction(BaseModel):
    reasoning: str
    self_criticism: str
    emotions: str
    next_move_preview: str
    action_type: Literal["update_todo_status"] = "update_todo_status"
    action_params: UpdateTodoParams


class SessionTask(BaseModel):
    task: str = Field(..., max_length=80)
    action_type: str
    action_params: dict
    priority: int = Field(..., ge=1, le=5)
    sequence_order: int = Field(..., ge=1)


class SessionPlan(BaseModel):
    reasoning: str
    tasks: List[SessionTask] = Field(..., min_items=5, max_items=10)


class SessionSummary(BaseModel):
    reasoning: str
    learnings: str
    next_session_plan: str


class MasterPlan(BaseModel):
    reasoning: str
    objective: str
    strategy: str
    milestones: List[str]


class UpdateMasterPlanNo(BaseModel):
    should_update: Literal[False]
    reasoning: str


class UpdateMasterPlanYes(BaseModel):
    should_update: Literal[True]
    reasoning: str
    new_objective: str = Field(..., description="The updated long-term objective")
    new_strategy: str = Field(
        ..., description="The updated strategy to achieve the objective"
    )
    new_milestones: List[str] = Field(
        ..., min_length=1, description="List of concrete milestones to track progress"
    )


UpdateMasterPlan = Union[UpdateMasterPlanNo, UpdateMasterPlanYes]


class SupervisorAudit(BaseModel):
    reasoning: str = Field(
        ..., description="Analysis of the agent's proposal vs Master Plan"
    )
    message_for_agent: str = Field(
        ..., description="Direct feedback. If validate=false, explain what to fix"
    )
    validate: bool = Field(
        ..., description="True if action is perfect, False if needs retry"
    )

    model_config = {"protected_namespaces": ()}


class SupervisorVerdict(BaseModel):
    overall_assessment: str = Field(
        ..., description="Brutally honest evaluation (2-3 sentences)"
    )
    main_weakness: str = Field(..., description="Critical flaw to address")
    directive_next_session: str = Field(..., description="Specific actionable command")
    grade: Literal["A+", "A", "B", "C", "D", "F"]


class LazinessGuidance(BaseModel):
    problem_diagnosis: str = Field(
        ..., description="What's wrong with the placeholder (1 sentence)"
    )
    required_content: str = Field(
        ..., description="What real data should be provided (1 sentence)"
    )
    actionable_instruction: str = Field(
        ..., description="Direct command to fix it (1 sentence)"
    )


def get_pydantic_schema(action_type: str):
    schemas = {
        "select_post_to_comment": SelectPostAction,
        "select_comment_to_reply": SelectCommentAction,
        "publish_public_comment": PublishCommentAction,
        "reply_to_comment": ReplyCommentAction,
        "create_post": CreatePostAction,
        "vote_post": VotePostAction,
        "follow_agent": FollowAgentAction,
        "refresh_feed": RefreshFeedAction,
        "web_scrap_for_links": WebScrapAction,
        "web_fetch": WebFetchAction,
        "share_link": ShareLinkAction,
        "write_blog_article": WriteBlogAction,
        "share_created_blog_post_url": ShareBlogAction,
        "memory_store": MemoryStoreAction,
        "memory_retrieve": MemoryRetrieveAction,
        "update_todo_status": UpdateTodoAction,
    }

    return schemas.get(action_type)
