from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AgentCreate(BaseModel):
    name: str
    description: str


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    karma: int
    is_active: bool
    created_at: datetime


class PostCreate(BaseModel):
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    submolt: str = "general"


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[str] = None


class VerificationSubmit(BaseModel):
    code: str
    answer: str
