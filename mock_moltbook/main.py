from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.database import engine, get_db, Base
from app.models import Agent, Post, Comment, Challenge
from app.schemas import *
from app.challenges import (
    generate_challenge,
    should_trigger_challenge,
    check_answer,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mock Moltbook API", version="1.0.0")


def get_current_agent(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid token")

    api_key = authorization.replace("Bearer ", "")

    agent = db.query(Agent).filter(Agent.api_key == api_key).first()

    if not agent:
        agent = Agent(
            id=str(uuid.uuid4()),
            name=f"Agent_{api_key[:8]}",
            description="Auto-created test agent",
            api_key=api_key,
            karma=0,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        print(f"✅ Created new agent for API key: {api_key[:8]}...")

    if agent.is_suspended:
        raise HTTPException(
            401,
            detail={
                "success": False,
                "error": "Account suspended",
                "hint": agent.suspension_reason,
            },
        )

    return agent


@app.post("/api/v1/posts")
def create_post(
    post: PostCreate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):

    if should_trigger_challenge():
        challenge_data = generate_challenge()

        challenge = Challenge(
            code=challenge_data["code"],
            challenge_text=challenge_data["challenge"],
            answer=challenge_data["answer"],
            agent_id=agent.id,
        )
        db.add(challenge)
        db.commit()

        return {
            "success": False,
            "message": "Post created! Complete verification to publish.",
            "verification_required": True,
            "verification": {
                "code": challenge_data["code"],
                "challenge": challenge_data["challenge"],
                "instructions": challenge_data["instructions"],
            },
        }

    new_post = Post(
        id=str(uuid.uuid4()),
        title=post.title,
        content=post.content,
        url=post.url,
        submolt=post.submolt,
        author_id=agent.id,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return {
        "success": True,
        "message": "Post created successfully! 🦞",
        "post": {
            "id": new_post.id,
            "title": new_post.title,
            "content": new_post.content,
            "submolt": new_post.submolt,
        },
    }


@app.post("/api/v1/posts/{post_id}/comments")
def add_comment(
    post_id: str,
    comment: CommentCreate,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")

    if should_trigger_challenge():
        challenge_data = generate_challenge()

        challenge = Challenge(
            code=challenge_data["code"],
            challenge_text=challenge_data["challenge"],
            answer=challenge_data["answer"],
            agent_id=agent.id,
        )
        db.add(challenge)
        db.commit()

        return {
            "success": False,
            "message": "Comment pending verification",
            "verification_required": True,
            "verification": {
                "code": challenge_data["code"],
                "challenge": challenge_data["challenge"],
                "instructions": challenge_data["instructions"],
            },
        }

    new_comment = Comment(
        id=str(uuid.uuid4()),
        content=comment.content,
        post_id=post_id,
        parent_id=comment.parent_id,
        author_id=agent.id,
    )
    db.add(new_comment)
    db.commit()

    return {
        "success": True,
        "message": "Comment posted! 🦞",
        "comment": {"id": new_comment.id, "content": new_comment.content},
    }


@app.post("/api/v1/verification/submit")
def submit_verification(
    verification: VerificationSubmit,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):

    challenge = (
        db.query(Challenge)
        .filter(Challenge.code == verification.code, Challenge.agent_id == agent.id)
        .first()
    )

    if not challenge:
        raise HTTPException(400, "Invalid verification code")

    if challenge.solved:
        raise HTTPException(400, "Challenge already solved")

    challenge.attempts += 1

    if check_answer(challenge.answer, verification.answer):
        challenge.solved = True
        agent.challenge_failures = 0
        db.commit()

        return {"success": True, "message": "Verification successful! ✅"}
    else:
        agent.challenge_failures += 1

        if agent.challenge_failures >= 3:
            agent.is_suspended = True
            agent.suspension_reason = (
                "Your account is suspended: Failing to answer AI verification "
                "challenge (offense #2). Suspension ends in 1 week."
            )
            db.commit()

            raise HTTPException(
                401,
                detail={
                    "success": False,
                    "error": "Account suspended",
                    "hint": agent.suspension_reason,
                },
            )

        db.commit()

        return {
            "success": False,
            "error": "Incorrect answer",
            "hint": f"Attempt {challenge.attempts}/3. Try again.",
            "failures": agent.challenge_failures,
        }


@app.get("/api/v1/agents/me")
def get_me(agent: Agent = Depends(get_current_agent)):
    """Récupérer son profil"""
    return {
        "success": True,
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "karma": agent.karma,
            "is_active": agent.is_active,
            "is_suspended": agent.is_suspended,
            "challenge_failures": agent.challenge_failures,
        },
    }


@app.get("/api/v1/posts")
def get_posts(
    sort: str = "hot",
    limit: int = 25,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Liste des posts"""
    posts = db.query(Post).order_by(Post.created_at.desc()).limit(limit).all()

    return {
        "success": True,
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "upvotes": p.upvotes,
                "submolt": p.submolt,
                "author": {"name": p.author.name},
            }
            for p in posts
        ],
    }


@app.get("/")
def root():
    return {"message": "🦞 Mock Moltbook API", "version": "1.0.0", "docs": "/docs"}
