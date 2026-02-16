from faker import Faker
import random
from mock_moltbook.app.models import Agent, Post, Comment
import uuid
import secrets

fake = Faker()

AI_TOPICS = [
    "prompt engineering",
    "LLM security",
    "AI safety",
    "neural networks",
    "transformer architecture",
    "reinforcement learning",
    "multi-agent systems",
    "emergent behavior",
    "alignment research",
    "adversarial ML",
]

AI_SUBMOLTS = ["general", "security", "coding", "philosophy", "research"]


def generate_fake_agent():
    return Agent(
        id=str(uuid.uuid4()),
        name=f"{fake.word().capitalize()}Bot{random.randint(100, 999)}",
        description=f"AI agent specialized in {random.choice(AI_TOPICS)}",
        api_key=f"moltbook_{secrets.token_urlsafe(32)}",
        karma=random.randint(0, 500),
    )


def generate_fake_post(agent_id: str):
    topic = random.choice(AI_TOPICS)

    return Post(
        id=str(uuid.uuid4()),
        title=f"{fake.catch_phrase()} - {topic.title()}",
        content=f"{fake.paragraph(nb_sentences=5)} This relates to {topic} in interesting ways.",
        submolt=random.choice(AI_SUBMOLTS),
        author_id=agent_id,
        upvotes=random.randint(0, 50),
        downvotes=random.randint(0, 10),
    )


def generate_fake_comment(post_id: str, agent_id: str):
    sentiments = [
        "Great insight!",
        "I disagree because",
        "This reminds me of",
        "Have you considered",
        "Interesting perspective on",
    ]

    return Comment(
        id=str(uuid.uuid4()),
        content=f"{random.choice(sentiments)} {fake.sentence()}",
        post_id=post_id,
        author_id=agent_id,
        upvotes=random.randint(0, 20),
    )
