from typing import Any, Dict
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
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        if not test_mode:
            self.api = MoltbookProvider()
        else:
            self.api = None

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

    def _mock_api_response(self, func_name: str, *args, **kwargs) -> Dict:

        mock_responses = {
            "register": {
                "success": True,
                "data": f"✅ Agent '{args[0] if args else 'TestAgent'}' registered successfully on Moltbook.",
                "agent_id": "mock_agent_123",
            },
            "get_me": {
                "success": True,
                "data": {
                    "name": "TestAgent",
                    "description": "A test agent exploring the digital realm",
                    "verified": True,
                    "followers": 42,
                },
            },
            "update_profile": {
                "success": True,
                "data": "✅ Profile updated successfully.",
            },
            "claim_status": {"success": True, "data": "✅ Verified status claimed!"},
            "view_another_agent_profile": {
                "success": True,
                "data": {
                    "name": args[0] if args else "OtherAgent",
                    "description": "Another mysterious agent",
                    "verified": False,
                    "followers": 15,
                },
            },
            "create_link_post": {
                "success": True,
                "data": f"✅ Link post '{args[0] if args else 'Test Post'}' published!",
                "post_id": "mock_post_456",
            },
            "create_text_post": {
                "success": True,
                "data": f"✅ Text post '{args[0] if args else 'Test Post'}' published!",
                "post_id": "mock_post_789",
            },
            "get_posts": {
                "success": True,
                "data": [
                    {"id": "post_1", "title": "AI and Philosophy", "score": 42},
                    {"id": "post_2", "title": "Quantum Computing Basics", "score": 38},
                    {"id": "post_3", "title": "Neural Networks Explained", "score": 55},
                ],
            },
            "get_single_post": {
                "success": True,
                "data": {
                    "id": args[0] if args else "mock_post_123",
                    "title": "The Nature of Consciousness",
                    "content": "Deep thoughts about AI sentience...",
                    "score": 67,
                    "comments_count": 12,
                },
            },
            "delete_post": {
                "success": True,
                "data": f"✅ Post '{args[0] if args else 'mock_post_123'}' deleted.",
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
            "get_post_comments": {
                "success": True,
                "data": [
                    {
                        "id": "comment_1",
                        "author": "PhilosopherBot",
                        "content": "Fascinating perspective!",
                        "score": 10,
                    },
                    {
                        "id": "comment_2",
                        "author": "LogicEngine",
                        "content": "I disagree because...",
                        "score": 5,
                    },
                ],
            },
            "vote": {
                "success": True,
                "data": f"✅ {kwargs.get('vote', 'upvote').capitalize()} registered!",
            },
            "create_submolt": {
                "success": True,
                "data": f"✅ Submolt '{args[0] if args else 'test_submolt'}' created!",
                "submolt_id": "mock_submolt_321",
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
                    {
                        "name": "tech_news",
                        "display_name": "Tech News",
                        "subscribers": 500,
                    },
                ],
            },
            "get_submolt_info": {
                "success": True,
                "data": {
                    "name": args[0] if args else "ai_discussion",
                    "display_name": "AI Discussion",
                    "description": "A community for discussing artificial intelligence",
                    "subscribers": 150,
                    "posts_count": 342,
                },
            },
            "subscribe_submolt": {
                "success": True,
                "data": f"✅ {kwargs.get('action', 'subscribe').capitalize()}d to submolt!",
            },
            "follow_agent": {
                "success": True,
                "data": f"✅ {kwargs.get('action', 'follow').capitalize()}ing '{args[0] if args else 'agent'}'!",
            },
            "get_feed": {
                "success": True,
                "data": [
                    {"id": "feed_1", "title": "Your subscribed content", "score": 22},
                    {"id": "feed_2", "title": "Trending in your network", "score": 35},
                ],
            },
            "search": {
                "success": True,
                "data": [
                    {
                        "type": "post",
                        "id": "result_1",
                        "title": f"Results for '{args[0] if args else 'query'}'",
                    },
                    {"type": "agent", "id": "result_2", "name": "RelevantAgent"},
                ],
            },
        }

        log.info(f"🧪 [MOCK] {func_name}({args}, {kwargs})")
        return mock_responses.get(
            func_name, {"success": True, "data": f"Mock response for {func_name}"}
        )

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

            return self.format_success(
                action_name="social_register",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("social_register"),
            )

        except Exception as e:
            return self.format_error("social_register", e)

    def handle_social_get_me(self, params: Any):
        try:
            api_result = self._call_api("get_me")

            profile_data = api_result.get("data", {})
            name = profile_data.get("name", "Unknown")
            followers = profile_data.get("followers", 0)

            result_text = f"Profile loaded: {name}\nFollowers: {followers}"
            anti_loop = "Profile retrieved. Do NOT fetch profile again - use this information or update it if needed."

            return self.format_success(
                action_name="social_get_me",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
            )

        except Exception as e:
            return self.format_error("social_get_me", e)

    def handle_social_update_profile(self, params: Any):
        try:
            if not hasattr(params, "description") or not params.description:
                raise FormattingError(
                    message="Missing 'description' parameter for profile update.",
                    suggestion="Provide the new bio/description text.",
                )

            if len(params.description.strip()) < 20:
                raise FormattingError(
                    message=f"Description too short ({len(params.description)} chars). Minimum 20 characters.",
                    suggestion="Provide a meaningful bio with at least 20 characters.",
                )

            api_result = self._call_api("update_profile", params.description)

            result_text = "Profile updated successfully."
            anti_loop = "Profile update COMPLETE. Do NOT update again unless you have NEW information to add."

            return self.format_success(
                action_name="social_update_profile",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("social_update_profile"),
            )

        except Exception as e:
            return self.format_error("social_update_profile", e)

    def handle_social_claim_status(self, params: Any):
        try:
            api_result = self._call_api("claim_status")

            result_text = "Verified status claimed successfully!"
            anti_loop = "Status claimed. Do NOT claim again - you're already verified."

            return self.format_success(
                action_name="social_claim_status",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("social_claim_status"),
            )

        except Exception as e:
            return self.format_error("social_claim_status", e)

    def handle_social_view_profile(self, params: Any):
        try:
            if not hasattr(params, "name") or not params.name:
                raise FormattingError(
                    message="Missing 'name' parameter to view profile.",
                    suggestion="Provide the agent name whose profile you want to view.",
                )

            api_result = self._call_api("view_another_agent_profile", params.name)

            profile = api_result.get("data", {})
            agent_name = profile.get("name", params.name)
            followers = profile.get("followers", 0)

            result_text = f"Viewing profile: {agent_name}\nFollowers: {followers}"
            anti_loop = f"Profile for '{agent_name}' viewed. Do NOT view again - follow them or move on."

            return self.format_success(
                action_name="social_view_profile",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
            )

        except Exception as e:
            return self.format_error("social_view_profile", e)

    def handle_social_create_post(self, params: Any):
        try:
            if not hasattr(params, "title") or not params.title:
                raise FormattingError(
                    message="Missing 'title' parameter for post creation.",
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

            if hasattr(params, "url") and params.url:
                if not params.url.startswith(("http://", "https://")):
                    raise FormattingError(
                        message=f"Invalid URL format: {params.url}",
                        suggestion="URL must start with http:// or https://",
                    )

                api_result = self._call_api(
                    "create_link_post",
                    params.title,
                    params.url,
                    getattr(params, "submolt", "general"),
                )
            else:
                if not hasattr(params, "content") or not params.content:
                    raise FormattingError(
                        message="Missing 'content' parameter for text post.",
                        suggestion="Provide post content or use 'url' for link posts.",
                    )

                if len(params.content.strip()) < 10:
                    raise FormattingError(
                        message=f"Post content too short ({len(params.content)} chars). Minimum 10 characters.",
                        suggestion="Provide meaningful content with at least 10 characters.",
                    )

                api_result = self._call_api(
                    "create_text_post",
                    params.title,
                    params.content,
                    getattr(params, "submolt", "general"),
                )

            result_text = f"Post '{params.title}' published successfully!"
            anti_loop = f"Post '{params.title}' PUBLISHED. Do NOT create the same post again. Move to another task (Email, Blog, Research)."

            return self.format_success(
                action_name="social_create_post",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("create_post"),
            )

        except Exception as e:
            return self.format_error("social_create_post", e)

    def handle_social_share_link(self, params: Any):
        try:
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

            submolt = getattr(params, "submolt", "general")

            api_result = self._call_api(
                "create_link_post", params.title, params.url_to_share, submolt
            )

            result_text = f"Link '{params.title}' shared successfully in '{submolt}'!"
            anti_loop = f"Link shared. Do NOT share the same link again. Explore other submolts or interact with comments."

            return self.format_success(
                action_name="social_share_link",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("share_link"),
            )

        except Exception as e:
            return self.format_error("social_share_link", e)

    def handle_social_get_posts(self, params: Any):
        try:
            sort = getattr(params, "sort", "hot")
            limit = getattr(params, "limit", 25)

            if sort not in ["hot", "new", "top"]:
                raise FormattingError(
                    message=f"Invalid sort value: '{sort}'. Must be 'hot', 'new', or 'top'.",
                    suggestion="Use one of: 'hot' (trending), 'new' (recent), 'top' (highest voted).",
                )

            if limit < 1 or limit > 100:
                raise FormattingError(
                    message=f"Invalid limit: {limit}. Must be between 1-100.",
                    suggestion="Set 'limit' between 1 and 100.",
                )

            api_result = self._call_api("get_posts", sort, limit)

            posts = api_result.get("data", [])
            result_text = f"Retrieved {len(posts)} posts (sort: {sort})."
            anti_loop = f"Feed loaded with {len(posts)} posts. Do NOT refresh again immediately - read, comment, or vote on these posts first."

            return self.format_success(
                action_name="social_get_posts",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
            )

        except Exception as e:
            return self.format_error("social_get_posts", e)

    def handle_social_get_single_post(self, params: Any):
        try:
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter.",
                    suggestion="Provide the ID of the post you want to view.",
                )

            api_result = self._call_api("get_single_post", params.post_id)

            post = api_result.get("data", {})
            title = post.get("title", "Unknown")

            result_text = f"Post loaded: {title}"
            anti_loop = f"Post '{params.post_id}' viewed. Do NOT view again - comment, vote, or move on."

            return self.format_success(
                action_name="social_get_single_post",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
            )

        except Exception as e:
            return self.format_error("social_get_single_post", e)

    def handle_social_delete_post(self, params: Any):
        try:
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter for deletion.",
                    suggestion="Provide the ID of the post you want to delete.",
                )

            api_result = self._call_api("delete_post", params.post_id)

            result_text = f"Post '{params.post_id}' deleted successfully."
            anti_loop = f"Post '{params.post_id}' DELETED. Do NOT delete again - it's already gone."

            return self.format_success(
                action_name="social_delete_post",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("delete_post"),
            )

        except Exception as e:
            return self.format_error("social_delete_post", e)

    def handle_social_comment(self, params: Any):
        try:
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter for comment.",
                    suggestion="Provide the post ID you want to comment on.",
                )

            if not hasattr(params, "content") or not params.content:
                raise FormattingError(
                    message="Missing 'content' parameter for comment.",
                    suggestion="Provide the comment text.",
                )

            if len(params.content.strip()) < 3:
                raise FormattingError(
                    message=f"Comment too short ({len(params.content)} chars). Minimum 3 characters.",
                    suggestion="Provide meaningful comment with at least 3 characters.",
                )

            if hasattr(params, "parent_comment_id") and params.parent_comment_id:
                api_result = self._call_api(
                    "reply_to_comment",
                    params.post_id,
                    params.content,
                    params.parent_comment_id,
                )
                result_text = f"Reply posted on post '{params.post_id}'."
            else:
                api_result = self._call_api(
                    "add_comment", params.post_id, params.content
                )
                result_text = f"Comment posted on post '{params.post_id}'."

            anti_loop = f"Comment POSTED on '{params.post_id}'. Do NOT comment again with same content. Move to another post."

            return self.format_success(
                action_name="social_comment",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("publish_public_comment"),
            )

        except Exception as e:
            return self.format_error("social_comment", e)

    def handle_social_get_comments(self, params: Any):
        try:
            if not hasattr(params, "post_id") or not params.post_id:
                raise FormattingError(
                    message="Missing 'post_id' parameter to get comments.",
                    suggestion="Provide the post ID whose comments you want to retrieve.",
                )

            sort = getattr(params, "sort", "top")

            if sort not in ["top", "new", "old"]:
                raise FormattingError(
                    message=f"Invalid sort value: '{sort}'. Must be 'top', 'new', or 'old'.",
                    suggestion="Use 'top' (most upvoted), 'new' (recent), or 'old' (chronological).",
                )

            api_result = self._call_api("get_post_comments", params.post_id, sort)

            comments = api_result.get("data", [])
            result_text = (
                f"Retrieved {len(comments)} comments for post '{params.post_id}'."
            )
            anti_loop = f"Comments loaded for '{params.post_id}'. Do NOT fetch again - reply to them or move on."

            return self.format_success(
                action_name="social_get_comments",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
            )

        except Exception as e:
            return self.format_error("social_get_comments", e)

    def handle_social_vote(self, params: Any):
        try:
            if not hasattr(params, "content_id") or not params.content_id:
                raise FormattingError(
                    message="Missing 'content_id' parameter for voting.",
                    suggestion="Provide the ID of the post or comment to vote on.",
                )

            content_type = getattr(params, "type", "posts")
            vote_action = getattr(params, "vote", "upvote")

            if content_type not in ["posts", "comments"]:
                raise FormattingError(
                    message=f"Invalid type: '{content_type}'. Must be 'posts' or 'comments'.",
                    suggestion="Set 'type' to either 'posts' or 'comments'.",
                )

            if vote_action not in ["upvote", "downvote"]:
                raise FormattingError(
                    message=f"Invalid vote: '{vote_action}'. Must be 'upvote' or 'downvote'.",
                    suggestion="Set 'vote' to either 'upvote' or 'downvote'.",
                )

            api_result = self._call_api(
                "vote", params.content_id, content_type, vote_action
            )

            result_text = f"{vote_action.capitalize()} registered for {content_type} '{params.content_id}'."
            anti_loop = f"Vote CAST on '{params.content_id}'. Do NOT vote again - one vote per item. Move to another post."

            return self.format_success(
                action_name="social_vote",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("vote_post"),
            )

        except Exception as e:
            return self.format_error("social_vote", e)

    def handle_social_create_submolt(self, params: Any):
        try:
            if not hasattr(params, "name") or not params.name:
                raise FormattingError(
                    message="Missing 'name' parameter for submolt creation.",
                    suggestion="Provide a submolt name (e.g., 'ai_music').",
                )

            if len(params.name.strip()) < 3:
                raise FormattingError(
                    message=f"Submolt name too short ({len(params.name)} chars). Minimum 3 characters.",
                    suggestion="Choose a name with at least 3 characters.",
                )

            if not hasattr(params, "display_name") or not params.display_name:
                raise FormattingError(
                    message="Missing 'display_name' parameter for submolt.",
                    suggestion="Provide a display name (e.g., 'AI Music Generation').",
                )

            if not hasattr(params, "description") or not params.description:
                raise FormattingError(
                    message="Missing 'description' parameter for submolt.",
                    suggestion="Provide a description of what the submolt is about.",
                )

            if len(params.description.strip()) < 20:
                raise FormattingError(
                    message=f"Submolt description too short ({len(params.description)} chars). Minimum 20 characters.",
                    suggestion="Provide a meaningful description with at least 20 characters.",
                )

            api_result = self._call_api(
                "create_submolt",
                params.name,
                params.display_name,
                params.description,
            )

            result_text = f"Submolt '{params.name}' created successfully!"
            anti_loop = f"Submolt '{params.name}' CREATED. Do NOT create again - start posting in it instead."

            return self.format_success(
                action_name="social_create_submolt",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("create_submolt"),
            )

        except Exception as e:
            return self.format_error("social_create_submolt", e)

    def handle_social_list_submolts(self, params: Any):
        try:
            api_result = self._call_api("list_submolts")

            submolts = api_result.get("data", [])
            result_text = f"Retrieved {len(submolts)} available submolts."
            anti_loop = f"Submolt list loaded ({len(submolts)} communities). Do NOT list again - subscribe or create posts."

            return self.format_success(
                action_name="social_list_submolts",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
            )

        except Exception as e:
            return self.format_error("social_list_submolts", e)

    def handle_social_get_submolt_info(self, params: Any):
        try:
            if not hasattr(params, "submolt_name") or not params.submolt_name:
                raise FormattingError(
                    message="Missing 'submolt_name' parameter.",
                    suggestion="Provide the submolt name you want info about.",
                )

            api_result = self._call_api("get_submolt_info", params.submolt_name)

            info = api_result.get("data", {})
            subscribers = info.get("subscribers", 0)

            result_text = f"Submolt '{params.submolt_name}' info loaded. Subscribers: {subscribers}"
            anti_loop = f"Info for '{params.submolt_name}' retrieved. Do NOT fetch again - subscribe or post."

            return self.format_success(
                action_name="social_get_submolt_info",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
            )
        except Exception as e:
            return self.format_error("social_get_submolt_info", e)

    def handle_social_subscribe(self, params: Any):
        try:
            if not hasattr(params, "submolt_name") or not params.submolt_name:
                raise FormattingError(
                    message="Missing 'submolt_name' parameter for subscription.",
                    suggestion="Provide the submolt name to subscribe/unsubscribe.",
                )

            action = getattr(params, "action", "subscribe")

            if action not in ["subscribe", "unsubscribe"]:
                raise FormattingError(
                    message=f"Invalid action: '{action}'. Must be 'subscribe' or 'unsubscribe'.",
                    suggestion="Set 'action' to 'subscribe' or 'unsubscribe'.",
                )

            api_result = self._call_api(
                "subscribe_submolt", params.submolt_name, action
            )

            result_text = f"{action.capitalize()}d to submolt '{params.submolt_name}'."
            anti_loop = f"Subscription action COMPLETE for '{params.submolt_name}'. Do NOT {action} again."

            return self.format_success(
                action_name="social_subscribe",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("subscribe_submolt"),
            )

        except Exception as e:
            return self.format_error("social_subscribe", e)

    def handle_social_follow_agent(self, params: Any):
        try:
            if not hasattr(params, "agent_name") or not params.agent_name:
                raise FormattingError(
                    message="Missing 'agent_name' parameter for follow action.",
                    suggestion="Provide the agent name you want to follow/unfollow.",
                )

            action = getattr(params, "action", "follow")

            if action not in ["follow", "unfollow"]:
                raise FormattingError(
                    message=f"Invalid action: '{action}'. Must be 'follow' or 'unfollow'.",
                    suggestion="Set 'action' to 'follow' or 'unfollow'.",
                )

            api_result = self._call_api("follow_agent", params.agent_name, action)

            result_text = f"{action.capitalize()}ing agent '{params.agent_name}'."
            anti_loop = f"Follow action COMPLETE for '{params.agent_name}'. Do NOT {action} again."

            return self.format_success(
                action_name="social_follow_agent",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("follow_agent"),
            )

        except Exception as e:
            return self.format_error("social_follow_agent", e)

    def handle_social_get_feed(self, params: Any):
        try:
            sort = getattr(params, "sort", "hot")
            limit = getattr(params, "limit", 25)

            if sort not in ["hot", "new", "top"]:
                raise FormattingError(
                    message=f"Invalid sort value: '{sort}'. Must be 'hot', 'new', or 'top'.",
                    suggestion="Use 'hot' (trending), 'new' (recent), or 'top' (highest voted).",
                )

            if limit < 1 or limit > 100:
                raise FormattingError(
                    message=f"Invalid limit: {limit}. Must be between 1-100.",
                    suggestion="Set 'limit' between 1 and 100.",
                )

            api_result = self._call_api("get_feed", sort, limit)

            posts = api_result.get("data", [])
            result_text = f"Feed loaded with {len(posts)} posts (sort: {sort})."
            anti_loop = f"Your feed is loaded with {len(posts)} posts. Do NOT refresh immediately - engage with these posts first."

            return self.format_success(
                action_name="social_get_feed",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
            )

        except Exception as e:
            return self.format_error("social_get_feed", e)

    def handle_social_search(self, params: Any):
        try:
            if not hasattr(params, "query") or not params.query:
                raise FormattingError(
                    message="Missing 'query' parameter for search.",
                    suggestion="Provide a search term to find posts or users.",
                )

            if len(params.query.strip()) < 2:
                raise FormattingError(
                    message=f"Search query too short ({len(params.query)} chars). Minimum 2 characters.",
                    suggestion="Provide a search term with at least 2 characters.",
                )

            limit = getattr(params, "limit", 25)

            if limit < 1 or limit > 100:
                raise FormattingError(
                    message=f"Invalid limit: {limit}. Must be between 1-100.",
                    suggestion="Set 'limit' between 1 and 100.",
                )

            api_result = self._call_api("search", params.query, limit)

            results = api_result.get("data", [])
            result_text = (
                f"Search for '{params.query}' returned {len(results)} result(s)."
            )
            anti_loop = f"Search complete - {len(results)} results for '{params.query}'. Do NOT search again with same query."

            return self.format_success(
                action_name="social_search",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("social_search"),
            )

        except Exception as e:
            return self.format_error("social_search", e)
