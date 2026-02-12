from typing import Any, Dict
from src.utils import log
from src.providers.moltbook_provider import MoltbookProvider
from src.utils.exceptions import APICommunicationError, SystemLogicError


class SocialHandler:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.api = MoltbookProvider()

    def _call_api(self, func, *args, **kwargs) -> Dict:
        try:
            result = func(*args, **kwargs)

            if result is None:
                raise APICommunicationError(f"API returned None during {func.__name__}")

            if isinstance(result, dict) and result.get("success") is False:
                error_info = result.get("error", "Unknown error")
                raise APICommunicationError(f"Moltbook API Error: {error_info}")

            return result
        except Exception as e:
            if isinstance(e, APICommunicationError):
                raise e
            log.critical(f"💥 Internal System Error in {func.__name__}: {str(e)}")
            raise SystemLogicError(f"Handler Failure: {str(e)}")

    def handle_social_register(self, params: Any):
        return self._call_api(self.api.register, params.name, params.description)

    def handle_social_get_me(self, params: Any):
        return self._call_api(self.api.get_me)

    def handle_social_update_profile(self, params: Any):
        return self._call_api(self.api.update_profile, params.description)

    def handle_social_claim_status(self, params: Any):
        return self._call_api(self.api.claim_status)

    def handle_social_view_profile(self, params: Any):
        return self._call_api(self.api.view_another_agent_profile, params.name)

    def handle_social_create_post(self, params: Any):
        if hasattr(params, "url") and params.url:
            return self._call_api(
                self.api.create_link_post,
                params.title,
                params.url,
                getattr(params, "submolt", "general"),
            )
        return self._call_api(
            self.api.create_text_post,
            params.title,
            params.content,
            getattr(params, "submolt", "general"),
        )

    def handle_social_get_posts(self, params: Any):
        return self._call_api(
            self.api.get_posts,
            getattr(params, "sort", "hot"),
            getattr(params, "limit", 25),
        )

    def handle_social_get_single_post(self, params: Any):
        return self._call_api(self.api.get_single_post, params.post_id)

    def handle_social_delete_post(self, params: Any):
        return self._call_api(self.api.delete_post, params.post_id)

    def handle_social_comment(self, params: Any):
        if hasattr(params, "parent_comment_id") and params.parent_comment_id:
            return self._call_api(
                self.api.reply_to_comment,
                params.post_id,
                params.content,
                params.parent_comment_id,
            )
        return self._call_api(self.api.add_comment, params.post_id, params.content)

    def handle_social_get_comments(self, params: Any):
        return self._call_api(
            self.api.get_post_comments, params.post_id, getattr(params, "sort", "top")
        )

    def handle_social_vote(self, params: Any):
        return self._call_api(
            self.api.vote,
            params.content_id,
            getattr(params, "type", "posts"),
            getattr(params, "vote", "upvote"),
        )

    def handle_social_create_submolt(self, params: Any):
        return self._call_api(
            self.api.create_submolt,
            params.name,
            params.display_name,
            params.description,
        )

    def handle_social_list_submolts(self, params: Any):
        return self._call_api(self.api.list_submolts)

    def handle_social_get_submolt_info(self, params: Any):
        return self._call_api(self.api.get_submolt_info, params.submolt_name)

    def handle_social_subscribe(self, params: Any):
        return self._call_api(
            self.api.subscribe_submolt,
            params.submolt_name,
            getattr(params, "action", "subscribe"),
        )

    def handle_social_follow_agent(self, params: Any):
        return self._call_api(
            self.api.follow_agent,
            params.agent_name,
            getattr(params, "action", "follow"),
        )

    def handle_social_get_feed(self, params: Any):
        return self._call_api(
            self.api.get_feed,
            getattr(params, "sort", "hot"),
            getattr(params, "limit", 25),
        )

    def handle_social_search(self, params: Any):
        return self._call_api(
            self.api.search, params.query, getattr(params, "limit", 25)
        )
