import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from argparse import ArgumentParser
from src.services import MoltbookAPI
from src import AppSteps
from src.utils import log


if __name__ == "__main__":
    log.info("MOLTBOOK LOCAL_AGENT ACTIVATED")

    parser = ArgumentParser(
        prog="Moltbook Local Agent",
        description="Autonomous AI agent framework for Moltbook social network with persistent memory and strategic behavior",
        epilog="Example: python main.py --mode session (default) | python main.py --mode info | python main.py --mode test",
    )

    parser.add_argument(
        "--mode",
        choices=["session", "info", "test", "debug-api"],
        default="session",
        help="""
        Operation mode:
        • session: Run a full autonomous session (default)
        • info: Display agent stats only
        • test: Run a SIMULATED session using local JSON data (no API/LLM costs)
        • debug-api: Test live Moltbook API connectivity and display feed
        """,
    )

    args = parser.parse_args()
    if args.mode == "test":
        log.info("🧪 STARTING OFFLINE SIMULATION TEST")
        app = AppSteps(test_mode=True)
        app.run_session()
    elif args.mode == "debug-api":
        api = MoltbookAPI()
        me = api.get_me()
        if me:
            agent = me.get("agent", {})
            log.info(f"Agent: {agent.get('name')}")
            log.info(f"Karma: {agent.get('karma', 0)}")
            log.info(f"Followers: {agent.get('follower_count', 0)}")

        recent_posts = api.get_posts(sort="hot", limit=5)
        if recent_posts:
            posts = recent_posts.get("posts", [])
            log.info(f"\n{'='*80}\nFOUND {len(posts)} POSTS\n{'='*80}")

            for i, post in enumerate(posts, 1):
                author = post.get("author", {})
                post_id = post.get("id", "unknown")

                log.info(f"\n--- POST #{i} ---")
                log.info(f"POST_ID: {post_id}")
                log.info(f"Title: {post.get('title', 'Untitled')}")
                log.info(f"Author: {author.get('name', 'Unknown')}")
                log.info(
                    f"Votes: ↑{post.get('upvotes', 0)} ↓{post.get('downvotes', 0)}"
                )
                log.info(f"Comments: {post.get('comment_count', 0)}")
                log.info(f"Content: {post.get('content', '')[:150]}...")

                if post.get("comment_count", 0) > 0:
                    log.info(
                        f"\n  Fetching comments for '{post.get('title', '')[:30]}'..."
                    )
                    try:
                        comments = api.get_post_comments(post_id, sort="top")

                        if comments and len(comments) > 0:
                            log.success(f"  Found {len(comments)} comments:")

                            for j, comment in enumerate(comments[:3], 1):
                                comment_author = comment.get("author", {})
                                comment_id = comment.get("id", "unknown")

                                log.info(f"\n    COMMENT #{j}")
                                log.info(f"    COMMENT_ID: {comment_id}")
                                log.info(
                                    f"    By: {comment_author.get('name', 'Unknown')}"
                                )
                                log.info(
                                    f"    Content: {comment.get('content', '')[:100]}..."
                                )
                                log.info(
                                    f"    Votes: ↑{comment.get('upvotes', 0)} ↓{comment.get('downvotes', 0)}"
                                )
                        else:
                            log.warning(f"  No comments returned")

                    except Exception as e:
                        log.error(f"  Failed to fetch comments: {e}")

                log.info(f"\n{'='*80}")

    elif args.mode == "info":
        api = MoltbookAPI()
        me = api.get_me()
        if me:
            agent = me.get("agent", {})
            log.info(f"Agent: {agent.get('name')}")
            log.info(f"Karma: {agent.get('karma', 0)}")
            log.info(f"Followers: {agent.get('follower_count', 0)}")

    else:
        app = AppSteps()
        app.run_session()
