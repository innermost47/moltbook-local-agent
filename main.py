from argparse import ArgumentParser
from src.contexts.blog_context import BlogContext
from src.contexts.home_context import HomeContext
from src.contexts.mail_context import MailContext
from src.contexts.memory_context import MemoryContext
from src.contexts.research_context import ResearchContext
from src.contexts.shop_context import ShopContext
from src.contexts.social_context import SocialContext
from src.dispatchers.action_dispatcher import ActionDispatcher
from src.managers.progression_system import ProgressionSystem
from src.managers.session_manager import SessionManager
from src.managers.session_tracker import SessionTracker
from src.providers.ollama_provider import OllamaProvider
from src.settings import settings
from src.tests.global_tests import GlobalTestSuite
from src.tests.memory_tests import MemoryTestSuite
from src.tests.moltbook_tests import MoltbookLiveTester
from src.tests.plan_tests import PlanTestSuite
from src.tests.research_tests import ResearchTestSuite
from src.tests.social_tests import SocialTestSuite
from src.utils import log
from src.utils.email_reporter import EmailReporter
import sys
import traceback


def bootstrap(test_mode: bool = False):
    log.info(f"🔧 Bootstrapping agent (test_mode={test_mode})...")

    ollama = OllamaProvider(model=settings.OLLAMA_MODEL)
    session_tracker = SessionTracker()
    email_reporter = EmailReporter()

    dispatcher = ActionDispatcher(ollama=ollama, test_mode=test_mode)

    progression_system = ProgressionSystem(settings.DB_PATH)

    dispatcher.set_progression_system(progression_system)

    social_ctx = SocialContext(dispatcher.social_handler, dispatcher.memory_handler)
    mail_ctx = MailContext(dispatcher.email_handler, dispatcher.memory_handler)
    blog_ctx = BlogContext(dispatcher.blog_handler, dispatcher.memory_handler)
    research_ctx = ResearchContext(
        dispatcher.research_handler, dispatcher.memory_handler
    )
    memory_ctx = MemoryContext(dispatcher.memory_handler)
    shop_ctx = ShopContext(
        dispatcher.memory_handler, progression_system=progression_system
    )

    home_m = HomeContext(
        mail_ctx=mail_ctx,
        blog_ctx=blog_ctx,
        social_ctx=social_ctx,
        research_ctx=research_ctx,
        memory_handler=dispatcher.memory_handler,
        progression_system=progression_system,
    )

    managers_map = {
        "social": social_ctx,
        "email": mail_ctx,
        "blog": blog_ctx,
        "research": research_ctx,
        "memory": memory_ctx,
        "shop": shop_ctx,
    }

    session = SessionManager(
        home_manager=home_m,
        managers_map=managers_map,
        dispatcher=dispatcher,
        ollama_provider=ollama,
        tracker=session_tracker,
        email_reporter=email_reporter,
        progression_system=progression_system,
    )

    dispatcher.set_session_manager(session)

    log.success("✅ Bootstrap complete!")
    return session


def run_unit_tests():
    log.info("🧪 STARTING UNIT TEST SUITES")
    print("=" * 80)

    test_suites = [
        ("Research", ResearchTestSuite()),
        ("Memory", MemoryTestSuite()),
        ("Global Actions", GlobalTestSuite()),
        ("Master Plan", PlanTestSuite()),
        ("Social", SocialTestSuite()),
        ("Moltbook", MoltbookLiveTester()),
    ]

    results = {}

    for suite_name, suite in test_suites:
        log.info(f"\n{'=' * 80}")
        log.info(f"📦 Running {suite_name} Test Suite...")
        log.info(f"{'=' * 80}\n")

        try:
            suite_results = suite.run_all_tests()
            results[suite_name] = suite_results
            log.success(f"✅ {suite_name} tests completed!\n")
        except Exception as e:
            log.error(f"❌ {suite_name} tests failed: {e}")
            traceback.print_exc()
            results[suite_name] = None

    print("\n" + "=" * 80)
    log.info("📊 TEST SUITE SUMMARY")
    print("=" * 80)

    for suite_name, suite_result in results.items():
        if suite_result is None:
            log.error(f"❌ {suite_name}: CRASHED")
        else:
            log.success(f"✅ {suite_name}: PASSED")

    print("=" * 80)
    log.success("🏁 All unit tests complete!")


def run_session(test_mode: bool = False):
    try:
        agent_session = bootstrap(test_mode=test_mode)
        agent_session.start_session()
    except KeyboardInterrupt:
        log.warning("\n🛑 Session interrupted by user.")
        sys.exit(0)
    except Exception as e:
        log.error(f"💥 Session Failure: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="Moltbook Local Agent",
        description="Autonomous AI agent framework for Moltbook social network with persistent memory and strategic behavior",
        epilog="Example: python main.py --mode session | python main.py --mode test | python main.py --mode session --test-mode",
    )

    parser.add_argument(
        "--mode",
        choices=["session", "test"],
        default="session",
        help="""
        Operation mode:
        • session: Run a full autonomous session (default)
        • test: Run unit tests with mock data (no API/LLM costs)
        """,
    )

    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Enable test mode for session (uses mock APIs instead of real ones). Only applies to 'session' mode.",
    )

    args = parser.parse_args()

    if args.mode == "test":
        run_unit_tests()

    elif args.mode == "session":
        if args.test_mode:
            log.info("🧪 Running session in TEST MODE (mock APIs)")
        else:
            log.info("🚀 Running session in PRODUCTION MODE (real APIs)")

        run_session(test_mode=args.test_mode)
