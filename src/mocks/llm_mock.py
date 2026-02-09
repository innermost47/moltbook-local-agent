import json
from src.utils import log


class LLMMock:
    def __init__(self):
        self.conversation_history = []
        self.completed_tasks = set()
        with open("tests/data/fake_ai_responses.json", "r", encoding="utf-8") as f:
            self.responses = json.load(f)
        self.step_counter = 0

    def generate_response(self, prompt, **kwargs):
        self.conversation_history.append({"role": "user", "content": prompt})
        p_lower = prompt.lower()

        model = kwargs.get("pydantic_model")
        model_name = model.__name__ if model else ""

        if model_name == "SessionPlan":
            key = "session_plan"
        elif model_name == "MasterPlan":
            key = "master_plan"
        elif model_name == "WriteBlogAction":
            key = "write_blog_article"
        elif model_name == "ShareBlogAction":
            key = "share_created_blog_post_url"
        elif model_name == "WebScrapAction":
            key = "web_scrap_for_links"
        elif model_name == "CreatePostAction":
            key = "create_post"
        elif model_name == "SelectPostAction":
            key = "select_post_to_comment"
        elif model_name == "PublishCommentAction":
            key = "publish_public_comment"
        elif model_name == "VotePostAction":
            key = "vote_post"
        elif model_name == "FollowAgentAction":
            key = "follow_agent"
        elif model_name == "MemoryStoreAction":
            key = "memory_store"
        elif model_name == "SessionSummary" or "summary" in p_lower:
            key = "session_summary"
        else:
            key = "select_post_to_comment"

        response_data = self.responses.get(key, {})

        if not response_data:
            log.warning(f"⚠️ [MOCK] No data found in JSON for key: {key}")

        json_string = json.dumps(response_data)

        if "agent_name" in kwargs and model_name not in ["SessionPlan", "MasterPlan"]:
            log.info(
                f"🧪 [MOCK] Phase: ACTION (Structured) | Key: {key} | Model: {model_name}"
            )
            return {"choices": [{"message": {"content": json_string}}]}

        log.info(f"🧪 [MOCK] Phase: PLANNING | Key: {key}")
        return json_string

    def get_main_system_prompt(self):
        return "STRICT MOCK SYSTEM PROMPT: You are a testing agent."

    def generate(self, prompt, **kwargs):
        response = self.generate_response(prompt, **kwargs)
        return response

    def trim_history(self, has_created_master_plan: bool = False):
        pass

    def generate_session_summary(self, prompt, **kwargs):
        log.info("🧪 [MOCK] Generating final session summary string...")
        summary_data = self.responses.get(
            "session_summary",
            {
                "reasoning": "Mock reasoning",
                "learnings": "Mock learnings",
                "next_session_plan": "Mock next plan",
            },
        )
        return json.dumps(summary_data)
