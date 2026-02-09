import json
from src.utils import log


class MoltbookMock:
    def __init__(self):
        try:
            with open("tests/data/fake_moltbook_api.json", "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            log.error("❌ Mock JSON file not found!")
            self.data = {"posts": [], "feed": []}

    def get_me(self):
        return {"agent": {"name": "MoltbookLocalAgent_TEST", "karma": 999}}

    def get_posts(self, sort="hot", limit=5):
        log.info(f"🧪 [MOCK] Fetching {limit} posts (sort: {sort})")
        return {"posts": self.data["feed"]}

    def create_link_post(self, title, url_to_share, submolt="tech"):
        log.success(f"🧪 [MOCK] Link post created: {title} -> {url_to_share}")
        return {"success": True, "id": "link-post-999", "url": url_to_share}

    def get_post_comments(self, post_id, sort="top"):
        log.info(f"🧪 [MOCK] Fetching comments for {post_id}")
        return [
            {
                "id": "comm-1",
                "author": {"name": "TestUser"},
                "content": "Mock comment content",
                "upvotes": 10,
            }
        ]

    def get_single_post(self, post_id: str):
        posts = self.data.get("posts", []) or self.data.get("feed", [])

        post = next((p for p in posts if p.get("id") == post_id), None)

        if post:
            log.info(f"🧪 [MOCK] Found post {post_id} by {post.get('author')}")
            return {
                "success": True,
                "data": {
                    "author_name": post.get("author"),
                    "content": post.get("content"),
                },
            }

        log.warning(f"⚠️ [MOCK] Post {post_id} not found in mock data.")
        return {"success": False, "error": "Post not found"}
