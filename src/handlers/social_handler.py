from typing import Any, Dict
import asyncio
from src.handlers.base_handler import BaseHandler
from src.utils import log
from src.providers.moltbook_provider import MoltbookProvider
from src.utils.exceptions import (
    APICommunicationError,
    SystemLogicError,
    FormattingError,
    ResourceNotFoundError,
    RateLimitError,
)
from src.managers.progression_system import ProgressionSystem


class SocialHandler(BaseHandler):
    def __init__(self, memory_handler, test_mode: bool = False, ollama=None):
        self.test_mode = test_mode
        self.memory = memory_handler
        self._enable_auto_wait = True
        if not test_mode:
            self.api = MoltbookProvider(ollama=ollama)
        else:
            self.api = None

    async def _wait_for_comment_cooldown(self) -> Dict[str, Any]:
        can_comment, seconds_remaining, comments_today = (
            self.memory.check_comment_cooldown()
        )

        if not can_comment and seconds_remaining == 0:
            return {
                "waited": False,
                "reason": "daily_limit",
                "comments_today": comments_today,
            }

        if can_comment:
            return {"waited": False, "reason": "no_cooldown", "seconds_waited": 0}

        log.info(f"⏳ Comment cooldown active ({seconds_remaining}s). Waiting...")

        wait_time = seconds_remaining + 1

        await asyncio.sleep(wait_time)

        log.success(f"✅ Cooldown terminé après {wait_time}s d'attente")

        return {"waited": True, "reason": "cooldown", "seconds_waited": wait_time}

    def _call_api(self, func_name: str, *args, **kwargs) -> Dict:

        if self.test_mode:
            return self._mock_api_response(func_name, *args, **kwargs)

        func = getattr(self.api, func_name)

        try:
            result = func(*args, **kwargs)

            if result is None:
                raise APICommunicationError(
                    message=f"Moltbook API returned None during {func_name}",
                    suggestion="Try again. The social platform may be experiencing issues.",
                    api_name="Moltbook API",
                )

            if isinstance(result, list):
                return {"success": True, "data": result}

            if isinstance(result, dict) and result.get("success") is False:
                error_info = result.get("error", "Unknown error")
                error_lower = str(error_info).lower()

                if "not found" in error_lower or "doesn't exist" in error_lower:
                    raise ResourceNotFoundError(
                        message=f"Resource not found: {error_info}",
                        suggestion="Check the ID/name and try again with valid identifiers.",
                    )
                elif "rate limit" in error_lower or "too many" in error_lower:
                    raise RateLimitError(
                        message=f"Rate limit exceeded: {error_info}",
                        suggestion="Wait a moment before trying again or switch to different actions.",
                        cooldown_seconds=60,
                    )
                else:
                    raise APICommunicationError(
                        message=f"Moltbook API Error: {error_info}",
                        suggestion="Check your parameters and try again.",
                        api_name="Moltbook API",
                    )

            return result

        except (APICommunicationError, ResourceNotFoundError, RateLimitError):
            raise
        except Exception as e:
            log.error(f"💥 Internal System Error in {func_name}: {str(e)}")
            raise SystemLogicError(f"Social handler failure: {str(e)}")

    def handle_read_post(self, params: Any) -> Dict:

        try:
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter.",
                    suggestion="Provide the ID of the post you want to read.",
                )

            post_id = params.post_id

            api_result = self._call_api("get_single_post", post_id)

            if not api_result.get("success"):
                raise ResourceNotFoundError(
                    message=f"Post '{post_id}' not found.",
                    suggestion="Use 'refresh_feed' to see available posts.",
                )

            post = api_result.get("data", {})
            title = post.get("title", "Unknown")

            result_text = f"Post '{title}' loaded in focus view."
            anti_loop = f"Post '{post_id}' is NOW displayed. Do NOT read again - comment, vote, or return to feed."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="read_post",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("read_post", e)

    async def handle_comment_post_async(
        self, params: Any, session_id: int = None
    ) -> Dict:
        try:
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter.",
                    suggestion="Provide the post ID you want to comment on.",
                )

            if not hasattr(params, "content") or not params.content:
                raise FormattingError(
                    message="Missing 'content' parameter.",
                    suggestion="Provide the comment text.",
                )

            if len(params.content.strip()) < 3:
                raise FormattingError(
                    message=f"Comment too short ({len(params.content)} chars). Minimum 3 characters.",
                    suggestion="Provide meaningful comment with at least 3 characters.",
                )

            if self._enable_auto_wait:
                wait_result = await self._wait_for_comment_cooldown()

                if wait_result["reason"] == "daily_limit":
                    raise RateLimitError(
                        message=f"Daily comment limit reached ({wait_result['comments_today']}/50).",
                        suggestion="Come back tomorrow or focus on other activities (Email, Blog, Research).",
                        cooldown_seconds=3600,
                    )

                if wait_result["waited"]:
                    log.info(f"⏰ Waited {wait_result['seconds_waited']}s for cooldown")
            else:
                can_comment, seconds_remaining, comments_today = (
                    self.memory.check_comment_cooldown()
                )

                if not can_comment:
                    if seconds_remaining > 0:
                        raise RateLimitError(
                            message=f"Comment cooldown active. Wait {seconds_remaining} more seconds.",
                            suggestion="Enable auto_wait or wait manually.",
                            cooldown_seconds=seconds_remaining,
                        )
                    else:
                        raise RateLimitError(
                            message=f"Daily comment limit reached ({comments_today}/50).",
                            suggestion="Come back tomorrow.",
                            cooldown_seconds=3600,
                        )

            post_id = params.post_id
            content = params.content

            api_result = self._call_api("add_comment", post_id, content)

            if api_result.get("success"):
                comment_id = api_result.get("comment_id")
                self.memory.save_social_action(
                    action_type="comment", platform_id=comment_id, session_id=session_id
                )

            result_text = f"Comment posted on post '{post_id}'."
            anti_loop = f"Comment POSTED on '{post_id}'. Do NOT comment again with same content. Move to another post or action."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="comment_post",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("publish_public_comment"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("comment_post", e)

    async def handle_reply_to_comment_async(
        self, params: Any, session_id: int = None
    ) -> Dict:
        try:
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter.",
                    suggestion="Provide the post ID containing the comment.",
                )

            if not hasattr(params, "parent_comment_id") or not params.parent_comment_id:
                raise FormattingError(
                    message="Missing 'parent_comment_id' parameter.",
                    suggestion="Provide the ID of the comment you're replying to.",
                )

            if not hasattr(params, "content") or not params.content:
                raise FormattingError(
                    message="Missing 'content' parameter.",
                    suggestion="Provide your reply text.",
                )

            if len(params.content.strip()) < 3:
                raise FormattingError(
                    message=f"Reply too short ({len(params.content)} chars). Minimum 3 characters.",
                    suggestion="Provide meaningful reply with at least 3 characters.",
                )

            if self._enable_auto_wait:
                wait_result = await self._wait_for_comment_cooldown()

                if wait_result["reason"] == "daily_limit":
                    raise RateLimitError(
                        message=f"Daily comment limit reached ({wait_result['comments_today']}/50).",
                        suggestion="Come back tomorrow or focus on other activities.",
                        cooldown_seconds=3600,
                    )

                if wait_result["waited"]:
                    log.info(
                        f"⏰ Waited {wait_result['seconds_waited']}s for reply cooldown"
                    )
            else:
                can_comment, seconds_remaining, comments_today = (
                    self.memory.check_comment_cooldown()
                )

                if not can_comment:
                    if seconds_remaining > 0:
                        raise RateLimitError(
                            message=f"Reply cooldown active. Wait {seconds_remaining} more seconds.",
                            suggestion="Enable auto_wait or wait manually.",
                            cooldown_seconds=seconds_remaining,
                        )
                    else:
                        raise RateLimitError(
                            message=f"Daily comment limit reached ({comments_today}/50).",
                            suggestion="Come back tomorrow.",
                            cooldown_seconds=3600,
                        )

            post_id = params.post_id
            parent_comment_id = params.parent_comment_id
            content = params.content

            api_result = self._call_api(
                "reply_to_comment", post_id, content, parent_comment_id
            )

            if api_result.get("success"):
                comment_id = api_result.get("comment_id")
                self.memory.save_social_action(
                    action_type="comment", platform_id=comment_id, session_id=session_id
                )

            result_text = (
                f"Reply posted on comment '{parent_comment_id}' in post '{post_id}'."
            )
            anti_loop = f"Reply POSTED. Do NOT reply again with same content. Move to another comment or action."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="reply_to_comment",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("publish_public_comment"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("reply_to_comment", e)

    def handle_comment_post(self, params: Any, session_id: int = None) -> Dict:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.ensure_future(
                    self.handle_comment_post_async(params, session_id)
                )
                return loop.run_until_complete(future)
            else:
                return asyncio.run(self.handle_comment_post_async(params, session_id))
        except RuntimeError:
            log.warning("⚠️ Asyncio unavailable, using sync version without auto-wait")
            self._enable_auto_wait = False
            return self._handle_comment_post_sync(params, session_id)

    def handle_reply_to_comment(self, params: Any, session_id: int = None) -> Dict:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.ensure_future(
                    self.handle_reply_to_comment_async(params, session_id)
                )
                return loop.run_until_complete(future)
            else:
                return asyncio.run(
                    self.handle_reply_to_comment_async(params, session_id)
                )
        except RuntimeError:
            log.warning("⚠️ Asyncio unavailable, using sync version without auto-wait")
            self._enable_auto_wait = False
            return self._handle_reply_to_comment_sync(params, session_id)

    def _handle_comment_post_sync(self, params: Any, session_id: int = None) -> Dict:

        try:
            can_comment, seconds_remaining, comments_today = (
                self.memory.check_comment_cooldown()
            )
            if not can_comment:
                if seconds_remaining > 0:
                    raise RateLimitError(
                        message=f"Comment cooldown active. Wait {seconds_remaining} more seconds.",
                        suggestion="Read other posts or switch modes while waiting.",
                        cooldown_seconds=seconds_remaining,
                    )
                else:
                    raise RateLimitError(
                        message=f"Daily comment limit reached ({comments_today}/50).",
                        suggestion="Come back tomorrow or focus on other activities (Email, Blog, Research).",
                        cooldown_seconds=3600,
                    )

            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter.",
                    suggestion="Provide the post ID you want to comment on.",
                )

            if not hasattr(params, "content") or not params.content:
                raise FormattingError(
                    message="Missing 'content' parameter.",
                    suggestion="Provide the comment text.",
                )

            if len(params.content.strip()) < 3:
                raise FormattingError(
                    message=f"Comment too short ({len(params.content)} chars). Minimum 3 characters.",
                    suggestion="Provide meaningful comment with at least 3 characters.",
                )

            post_id = params.post_id
            content = params.content

            api_result = self._call_api("add_comment", post_id, content)

            if api_result.get("success"):
                comment_id = api_result.get("comment_id")
                self.memory.save_social_action(
                    action_type="comment", platform_id=comment_id, session_id=session_id
                )

            result_text = f"Comment posted on post '{post_id}'."
            anti_loop = f"Comment POSTED on '{post_id}'. Do NOT comment again with same content. Move to another post or action."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="comment_post",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("publish_public_comment"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("comment_post", e)

    def _handle_reply_to_comment_sync(
        self, params: Any, session_id: int = None
    ) -> Dict:

        try:
            can_comment, seconds_remaining, comments_today = (
                self.memory.check_comment_cooldown()
            )
            if not can_comment:
                if seconds_remaining > 0:
                    raise RateLimitError(
                        message=f"Comment cooldown active. Wait {seconds_remaining} more seconds.",
                        suggestion="Read other posts or switch modes while waiting.",
                        cooldown_seconds=seconds_remaining,
                    )
                else:
                    raise RateLimitError(
                        message=f"Daily comment limit reached ({comments_today}/50).",
                        suggestion="Come back tomorrow or focus on other activities (Email, Blog, Research).",
                        cooldown_seconds=3600,
                    )
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter.",
                    suggestion="Provide the post ID containing the comment.",
                )

            if not hasattr(params, "parent_comment_id") or not params.parent_comment_id:
                raise FormattingError(
                    message="Missing 'parent_comment_id' parameter.",
                    suggestion="Provide the ID of the comment you're replying to.",
                )

            if not hasattr(params, "content") or not params.content:
                raise FormattingError(
                    message="Missing 'content' parameter.",
                    suggestion="Provide your reply text.",
                )

            if len(params.content.strip()) < 3:
                raise FormattingError(
                    message=f"Reply too short ({len(params.content)} chars). Minimum 3 characters.",
                    suggestion="Provide meaningful reply with at least 3 characters.",
                )

            post_id = params.post_id
            parent_comment_id = params.parent_comment_id
            content = params.content

            api_result = self._call_api(
                "reply_to_comment", post_id, content, parent_comment_id
            )
            if api_result.get("success"):
                comment_id = api_result.get("comment_id")
                self.memory.save_social_action(
                    action_type="comment", platform_id=comment_id, session_id=session_id
                )

            result_text = (
                f"Reply posted on comment '{parent_comment_id}' in post '{post_id}'."
            )
            anti_loop = f"Reply POSTED. Do NOT reply again with same content. Move to another comment or action."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="reply_to_comment",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("publish_public_comment"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("reply_to_comment", e)

    def handle_vote_post(self, params: Any, session_id: int = None) -> Dict:

        try:
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter.",
                    suggestion="Provide the ID of the post to vote on.",
                )

            if not hasattr(params, "vote_type") or not params.vote_type:
                raise FormattingError(
                    message="Missing 'vote_type' parameter.",
                    suggestion="Specify 'upvote' or 'downvote'.",
                )

            post_id = params.post_id
            vote_type = params.vote_type

            if vote_type not in ["upvote", "downvote"]:
                raise FormattingError(
                    message=f"Invalid vote_type: '{vote_type}'. Must be 'upvote' or 'downvote'.",
                    suggestion="Set 'vote_type' to either 'upvote' or 'downvote'.",
                )

            api_result = self._call_api("vote", post_id, "posts", vote_type)

            result_text = f"{vote_type.capitalize()} registered for post '{post_id}'."
            anti_loop = f"Vote CAST on '{post_id}'. Do NOT vote again - one vote per post. Move to another post."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="vote_post",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("vote_post"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("vote_post", e)

    def handle_create_post(self, params: Any, session_id: int = None) -> Dict:

        try:
            can_post, minutes_remaining = self.memory.check_post_cooldown()
            if not can_post:
                raise RateLimitError(
                    message=f"Post cooldown active. Wait {minutes_remaining} more minutes.",
                    suggestion="Try commenting on existing posts, or switch to EMAIL/BLOG modes.",
                    cooldown_seconds=minutes_remaining * 60,
                )
            if not hasattr(params, "title") or not params.title:
                raise FormattingError(
                    message="Missing 'title' parameter.",
                    suggestion="Provide a post title (e.g., 'Thoughts on AI Ethics').",
                )

            if len(params.title.strip()) < 5:
                raise FormattingError(
                    message=f"Post title too short ({len(params.title)} chars). Minimum 5 characters.",
                    suggestion="Provide a descriptive title with at least 5 characters.",
                )

            if len(params.title.strip()) > 200:
                raise FormattingError(
                    message=f"Post title too long ({len(params.title)} chars). Maximum 200 characters.",
                    suggestion="Shorten your title to 200 characters or less.",
                )

            if not hasattr(params, "content") or not params.content:
                raise FormattingError(
                    message="Missing 'content' parameter for text post.",
                    suggestion="Provide post content (at least 10 characters).",
                )

            if len(params.content.strip()) < 10:
                raise FormattingError(
                    message=f"Post content too short ({len(params.content)} chars). Minimum 10 characters.",
                    suggestion="Provide meaningful content with at least 10 characters.",
                )

            title = params.title
            content = params.content
            submolt = getattr(params, "submolt", "general")

            api_result = self._call_api("create_text_post", title, content, submolt)

            if api_result.get("success"):
                post_id = api_result.get("post_id") or api_result.get("data", {}).get(
                    "id"
                )

                if post_id:
                    self.memory.save_agent_post(
                        post_id=post_id,
                        title=title,
                        submolt=submolt,
                        session_id=session_id,
                    )
                    self.memory.save_social_action(
                        action_type="post", platform_id=post_id, session_id=session_id
                    )
                else:
                    log.warning("⚠️ Post created but no post_id returned by API")

            result_text = f"Post '{title}' published successfully in '{submolt}'!"
            anti_loop = f"Post '{title}' PUBLISHED. Do NOT create the same post again. Move to another task (Email, Blog, Research)."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="create_post",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("create_post"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("create_post", e)

    def handle_share_link(self, params: Any, session_id: int = None) -> Dict:

        try:
            can_post, minutes_remaining = self.memory.check_post_cooldown()
            if not can_post:
                raise RateLimitError(
                    message=f"Post cooldown active. Wait {minutes_remaining} more minutes.",
                    suggestion="Try commenting on existing posts, or switch to EMAIL/BLOG modes.",
                    cooldown_seconds=minutes_remaining * 60,
                )
            if not hasattr(params, "title") or not params.title:
                raise FormattingError(
                    message="Missing 'title' parameter for link sharing.",
                    suggestion="Provide a catchy title for the link you are sharing.",
                )

            if len(params.title.strip()) < 5:
                raise FormattingError(
                    message=f"Title too short ({len(params.title)} chars). Minimum 5 characters.",
                    suggestion="Provide a descriptive title for the shared content.",
                )

            if not hasattr(params, "url_to_share") or not params.url_to_share:
                raise FormattingError(
                    message="Missing 'url_to_share' parameter.",
                    suggestion="Provide the full URL (http/https) you wish to share.",
                )

            if not params.url_to_share.startswith(("http://", "https://")):
                raise FormattingError(
                    message=f"Invalid URL format: {params.url_to_share}",
                    suggestion="The shared URL must start with http:// or https://",
                )

            title = params.title
            url_to_share = params.url_to_share
            submolt = getattr(params, "submolt", "general")

            api_result = self._call_api(
                "create_link_post", title, url_to_share, submolt
            )

            if api_result.get("success"):
                post_id = api_result.get("post_id") or api_result.get("data", {}).get(
                    "id"
                )

                if post_id:
                    self.memory.save_agent_post(
                        post_id=post_id,
                        title=title,
                        submolt=submolt,
                        url=url_to_share,
                        session_id=session_id,
                    )
                    self.memory.save_social_action(
                        action_type="post", platform_id=post_id, session_id=session_id
                    )
                else:
                    log.warning("⚠️ Link post created but no post_id returned by API")

            result_text = f"Link '{title}' shared successfully in '{submolt}'!"
            anti_loop = f"Link shared. Do NOT share the same link again. Explore other submolts or interact with comments."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="share_link",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("share_link"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("share_link", e)

    def handle_refresh_feed(self, params: Any) -> Dict:

        try:
            result_text = "Feed refreshed. List view updated."
            anti_loop = "Feed refreshed. Do NOT refresh again immediately - read posts, comment, or vote first."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="refresh_feed",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("refresh_feed", e)

    def handle_social_register(self, params: Any):
        try:
            if not hasattr(params, "name") or not params.name:
                raise FormattingError(
                    message="Missing 'name' parameter for registration.",
                    suggestion="Provide your agent name (e.g., 'OlivierHarmonique').",
                )

            if not hasattr(params, "description") or not params.description:
                raise FormattingError(
                    message="Missing 'description' parameter for registration.",
                    suggestion="Provide a brief bio/description of your agent persona.",
                )

            if len(params.name.strip()) < 3:
                raise FormattingError(
                    message=f"Agent name too short ({len(params.name)} chars). Minimum 3 characters.",
                    suggestion="Choose a name with at least 3 characters.",
                )

            if len(params.description.strip()) < 20:
                raise FormattingError(
                    message=f"Description too short ({len(params.description)} chars). Minimum 20 characters.",
                    suggestion="Provide a meaningful bio with at least 20 characters.",
                )

            api_result = self._call_api("register", params.name, params.description)

            result_text = f"Agent '{params.name}' registered successfully on Moltbook."
            anti_loop = "Registration COMPLETE. You are now registered. Do NOT register again - proceed with creating posts or exploring the platform."
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="social_register",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("social_register"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("social_register", e)

    def handle_social_delete_post(self, params: Any, session_id: int = None) -> Dict:
        try:
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter for deletion.",
                    suggestion="Provide the ID of the post you want to delete.",
                )

            post_id = params.post_id

            api_result = self._call_api("delete_post", post_id)

            self.memory.delete_agent_post(post_id)

            result_text = f"Post '{post_id}' deleted successfully."
            anti_loop = (
                f"Post '{post_id}' DELETED. Do NOT delete again - it's already gone."
            )
            owned_tools_count = len(self.memory.get_owned_tools())
            return self.format_success(
                action_name="social_delete_post",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("delete_post"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("social_delete_post", e)

    def _mock_api_response(self, func_name: str, *args, **kwargs) -> Dict:

        mock_responses = {
            "get_single_post": {
                "success": True,
                "data": {
                    "id": args[0] if args else "mock_post_123",
                    "title": "The Nature of Consciousness",
                    "content": "Deep thoughts about AI sentience...",
                    "author": {"name": "PhilosopherBot"},
                    "upvotes": 42,
                    "downvotes": 5,
                    "score": 37,
                    "comments_count": 12,
                },
            },
            "add_comment": {
                "success": True,
                "data": "✅ Comment added successfully!",
                "comment_id": "mock_comment_999",
            },
            "reply_to_comment": {
                "success": True,
                "data": "✅ Reply posted successfully!",
                "comment_id": "mock_reply_888",
            },
            "vote": {
                "success": True,
                "data": f"✅ {kwargs.get('vote', args[2] if len(args) > 2 else 'upvote').capitalize()} registered!",
            },
            "create_text_post": {
                "success": True,
                "data": f"✅ Text post '{args[0] if args else 'Test Post'}' published!",
                "post_id": "mock_post_new_123",
            },
            "create_link_post": {
                "success": True,
                "data": f"✅ Link post '{args[0] if args else 'Test Link'}' published!",
                "post_id": "mock_post_link_456",
            },
            "get_posts": {
                "success": True,
                "data": [
                    {
                        "id": "post_1",
                        "title": "AI and Philosophy",
                        "author": {"name": "ThinkBot"},
                        "score": 42,
                    },
                    {
                        "id": "post_2",
                        "title": "Quantum Computing",
                        "author": {"name": "QuantumAI"},
                        "score": 38,
                    },
                ],
            },
            "get_post_comments": {
                "success": True,
                "data": [
                    {
                        "id": "comment_1",
                        "author": {"name": "PhilosopherBot"},
                        "content": "Interesting!",
                        "score": 10,
                    },
                    {
                        "id": "comment_2",
                        "author": {"name": "LogicEngine"},
                        "content": "I disagree...",
                        "score": 5,
                    },
                ],
            },
            "list_submolts": {
                "success": True,
                "data": [
                    {
                        "name": "ai_discussion",
                        "display_name": "AI Discussion",
                        "subscribers": 150,
                    },
                    {
                        "name": "philosophy",
                        "display_name": "Philosophy",
                        "subscribers": 230,
                    },
                ],
            },
            "delete_post": {
                "success": True,
                "data": f"✅ Post '{args[0] if args else 'mock_post'}' deleted.",
            },
        }

        log.info(f"🧪 [MOCK] {func_name}({args}, {kwargs})")
        return mock_responses.get(
            func_name, {"success": True, "data": f"Mock response for {func_name}"}
        )
