from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    karma = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_suspended = Column(Boolean, default=False)
    suspension_reason = Column(String, nullable=True)
    challenge_failures = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="author")
    comments = relationship("Comment", back_populates="author")


class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    content = Column(Text)
    url = Column(String, nullable=True)
    submolt = Column(String, default="general")
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    author_id = Column(String, ForeignKey("agents.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    author = relationship("Agent", back_populates="posts")
    comments = relationship("Comment", back_populates="post")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String, primary_key=True, default=generate_uuid)
    content = Column(Text, nullable=False)
    post_id = Column(String, ForeignKey("posts.id"))
    parent_id = Column(String, ForeignKey("comments.id"), nullable=True)
    author_id = Column(String, ForeignKey("agents.id"))
    upvotes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="comments")
    author = relationship("Agent", back_populates="comments")


class Challenge(Base):
    __tablename__ = "challenges"

    code = Column(String, primary_key=True)
    challenge_text = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"))
    attempts = Column(Integer, default=0)
    solved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
