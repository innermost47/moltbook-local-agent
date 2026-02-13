from src.providers.moltbook_provider import MoltbookProvider
from src.utils import log


class MoltbookLiveTester:
    def __init__(self):
        log.info("📡 Initializing Moltbook Live Provider...")
        self.provider = MoltbookProvider()
        self.results = {}

    def run_test(self, name: str, func, *args, **kwargs):
        log.info(f"--- ⚡ EXECUTING LIVE CALL: {name} ---")
        try:
            result = func(*args, **kwargs)

            if result is None:
                log.error(f"❌ {name} returned None (Possible timeout or 404)")
            elif isinstance(result, dict) and result.get("success") is False:
                log.error(f"❌ {name} failed: {result.get('error')}")
            else:
                log.success(f"✅ {name} successful")
                preview = (
                    str(result)[:500] + "..." if len(str(result)) > 500 else str(result)
                )
                print(f"Data: {preview}")

            self.results[name] = result
            return result
        except Exception as e:
            log.error(f"💥 Critical error during {name}: {e}")
            return None

    def run_all_tests(self):
        log.info("🚀 Starting Real API Calls...")
        print("=" * 80)

        self.run_test("GET_ME", self.provider.get_me)

        self.run_test("LIST_SUBMOLTS", self.provider.list_submolts)

        posts = self.run_test("GET_POSTS", self.provider.get_posts, sort="hot", limit=5)

        self.run_test("SEARCH", self.provider.search, query="AI", limit=3)

        self.run_test("GET_FEED", self.provider.get_feed, sort="new", limit=5)

        if posts and isinstance(posts, dict) and posts.get("posts"):
            first_post_id = posts["posts"][0].get("id")
            if first_post_id:
                self.run_test(
                    f"GET_COMMENTS_FOR_{first_post_id}",
                    self.provider.get_post_comments,
                    post_id=first_post_id,
                )

        self.summary()

    def summary(self):
        print("\n" + "=" * 80)
        successes = sum(
            1
            for r in self.results.values()
            if r and (not isinstance(r, dict) or r.get("success") != False)
        )
        log.info(
            f"📊 LIVE API SUMMARY: {successes}/{len(self.results)} calls succeeded."
        )
        print("=" * 80)
