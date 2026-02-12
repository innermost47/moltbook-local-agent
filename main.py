import sys
import traceback
from argparse import ArgumentParser
from src.utils import log
from src.utils.email_reporter import EmailReporter
from src.providers.ollama_provider import OllamaProvider
from src.dispatchers.action_dispatcher import ActionDispatcher

from src.managers.social_context_manager import SocialContextManager
from src.managers.mail_context_manager import MailContextManager
from src.managers.blog_context_manager import BlogContextManager
from src.managers.research_context_manager import ResearchContextManager
from src.managers.memory_context_manager import MemoryContextManager
from src.managers.home_manager import HomeManager
from src.managers.session_manager import SessionManager
from src.managers.session_tracker import SessionTracker

from src.tests.research_tests import ResearchTestSuite
from src.tests.memory_tests import MemoryTestSuite
from src.tests.global_tests import GlobalTestSuite
from src.tests.plan_tests import PlanTestSuite


def bootstrap():

    ollama = OllamaProvider(model="qwen2.5:7b")
    session_tracker = SessionTracker()
    email_reporter = EmailReporter()
    dispatcher = ActionDispatcher()

    social_ctx = SocialContextManager(dispatcher.social_handler)
    mail_ctx = MailContextManager(dispatcher.email_handler)
    blog_ctx = BlogContextManager(dispatcher.blog_handler)
    research_ctx = ResearchContextManager(dispatcher.research_handler)
    memory_ctx = MemoryContextManager(dispatcher.memory_handler)

    home_m = HomeManager(
        mail_ctx=mail_ctx,
        blog_ctx=blog_ctx,
        social_ctx=social_ctx,
        research_ctx=research_ctx,
        memory_handler=dispatcher.memory_handler,
    )

    managers_map = {
        "social": social_ctx,
        "email": mail_ctx,
        "blog": blog_ctx,
        "research": research_ctx,
        "memory": memory_ctx,
    }

    session = SessionManager(
        home_manager=home_m,
        managers_map=managers_map,
        dispatcher=dispatcher,
        ollama_provider=ollama,
        tracker=session_tracker,
        email_reporter=email_reporter,
    )

    dispatcher.set_session_manager(session)

    return session


def test():
    research_test_suite = ResearchTestSuite()
    memory_test_suite = MemoryTestSuite()
    global_test_suite = GlobalTestSuite()
    plan_test_suite = PlanTestSuite()
    research_test_suite.run_all_tests()
    memory_test_suite.run_all_tests()
    global_test_suite.run_all_tests()
    plan_test_suite.run_all_tests()


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="Moltbook Local Agent",
        description="Autonomous AI agent framework for Moltbook social network with persistent memory and strategic behavior",
        epilog="Example: python main.py --mode session (default) | python main.py --mode test",
    )

    parser.add_argument(
        "--mode",
        choices=["session", "test"],
        default="session",
        help="""
        Operation mode:
        • session: Run a full autonomous session (default)
        • test: Run a SIMULATED session using local JSON data (no API/LLM costs)
        """,
    )

    args = parser.parse_args()
    if args.mode == "test":
        log.info("🧪 STARTING SIMULATION TEST")
        test()
    else:
        try:
            agent_session = bootstrap()
            agent_session.start_session()
        except KeyboardInterrupt:
            log.warning("\n🛑 Session interrupted by user.")
            sys.exit(0)
        except Exception as e:
            log.error(f"💥 Boot Failure: {e}")

            traceback.print_exc()
            sys.exit(1)
