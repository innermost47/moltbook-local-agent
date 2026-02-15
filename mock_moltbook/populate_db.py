import sys

sys.path.append("..")

from mock_moltbook.app.database import SessionLocal, engine, Base
from mock_moltbook.app.fake_content import (
    generate_fake_agent,
    generate_fake_post,
    generate_fake_comment,
)


def populate():

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    print("🦞 Populating Mock Moltbook DB...")

    agents = []
    for i in range(50):
        agent = generate_fake_agent()
        db.add(agent)
        agents.append(agent)

    db.commit()
    print(f"✅ Created {len(agents)} agents")

    posts = []
    for i in range(200):
        agent = agents[i % len(agents)]
        post = generate_fake_post(agent.id)
        db.add(post)
        posts.append(post)

    db.commit()
    print(f"✅ Created {len(posts)} posts")

    for i in range(500):
        post = posts[i % len(posts)]
        agent = agents[i % len(agents)]
        comment = generate_fake_comment(post.id, agent.id)
        db.add(comment)

    db.commit()
    print(f"✅ Created 500 comments")

    print("🎉 Database populated successfully!")
    db.close()


if __name__ == "__main__":
    populate()
