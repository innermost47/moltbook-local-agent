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
        elif model_name == "WebFetchAction":
            key = "web_fetch"
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
        elif model_name == "EmailReadAction":
            key = "email_read"
        elif model_name == "EmailSendAction":
            key = "email_send"
        elif model_name == "EmailDeleteAction":
            key = "email_delete"
        elif model_name == "EmailArchiveAction":
            key = "email_archive"
        elif model_name == "EmailMarkReadAction":
            key = "email_mark_read"
        elif model_name == "SessionSummary" or "summary" in p_lower:
            key = "session_summary"
        elif model_name == "UpdateTodoAction":
            key = "update_todo_status"
        else:
            key = "select_post_to_comment"

        response_data = self.responses.get(key, {})

        if not response_data:
            log.warning(f"⚠️ [MOCK] No data found in JSON for key: {key}")

        structured_dict = {
            "choices": [{"message": {"content": json.dumps(response_data)}}]
        }

        if "agent_name" in kwargs and model_name not in ["SessionPlan", "MasterPlan"]:
            log.info(f"🧪 [MOCK] Returning DICT for {model_name}")
            return structured_dict

        return json.dumps(response_data)

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

    def generate_simple(self, prompt: str, max_tokens: int = 300) -> str:
        log.info("🧪 [MOCK] Generating simple summary...")

        if "session_summary" in self.responses:
            summary_data = self.responses["session_summary"]
            return (
                f"REASONING: {summary_data.get('reasoning')}\n"
                f"LEARNINGS: {summary_data.get('learnings')}\n"
                f"STATUS: {summary_data.get('status_update')}"
            )

        return "The session was executed successfully. All technical tasks reached their intended endpoints."
