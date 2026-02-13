from typing import Any, Dict
from src.utils import log
from src.providers.moltbook_provider import MoltbookProvider
from src.utils.exceptions import (
    APICommunicationError,
    SystemLogicError,
    FormattingError,
    ResourceNotFoundError,
    RateLimitError,
)


class SocialHandler:
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

        return self._call_api("register", params.name, params.description)

    def handle_social_get_me(self, params: Any):
        return self._call_api("get_me")

    def handle_social_update_profile(self, params: Any):

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

        return self._call_api("update_profile", params.description)

    def handle_social_claim_status(self, params: Any):
        return self._call_api("claim_status")

    def handle_social_view_profile(self, params: Any):

        if not hasattr(params, "name") or not params.name:
            raise FormattingError(
                message="Missing 'name' parameter to view profile.",
                suggestion="Provide the agent name whose profile you want to view.",
            )

        return self._call_api("view_another_agent_profile", params.name)

    def handle_social_create_post(self, params: Any):

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

            return self._call_api(
                "create_link_post",
                params.title,
                params.url,
                getattr(params, "submolt", "general"),
            )

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

        return self._call_api(
            "create_text_post",
            params.title,
            params.content,
            getattr(params, "submolt", "general"),
        )

    def handle_social_get_posts(self, params: Any):

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

        return self._call_api("get_posts", sort, limit)

    def handle_social_get_single_post(self, params: Any):

        if not hasattr(params, "post_id") or not params.post_id:
            raise FormattingError(
                message="Missing 'post_id' parameter.",
                suggestion="Provide the ID of the post you want to view.",
            )

        return self._call_api("get_single_post", params.post_id)

    def handle_social_delete_post(self, params: Any):

        if not hasattr(params, "post_id") or not params.post_id:
            raise FormattingError(
                message="Missing 'post_id' parameter for deletion.",
                suggestion="Provide the ID of the post you want to delete.",
            )

        return self._call_api("delete_post", params.post_id)

    def handle_social_comment(self, params: Any):

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
            return self._call_api(
                "reply_to_comment",
                params.post_id,
                params.content,
                params.parent_comment_id,
            )

        return self._call_api("add_comment", params.post_id, params.content)

    def handle_social_get_comments(self, params: Any):

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

        return self._call_api("get_post_comments", params.post_id, sort)

    def handle_social_vote(self, params: Any):

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

        return self._call_api("vote", params.content_id, content_type, vote_action)

    def handle_social_create_submolt(self, params: Any):

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

        return self._call_api(
            "create_submolt",
            params.name,
            params.display_name,
            params.description,
        )

    def handle_social_list_submolts(self, params: Any):
        return self._call_api("list_submolts")

    def handle_social_get_submolt_info(self, params: Any):

        if not hasattr(params, "submolt_name") or not params.submolt_name:
            raise FormattingError(
                message="Missing 'submolt_name' parameter.",
                suggestion="Provide the submolt name you want info about.",
            )

        return self._call_api("get_submolt_info", params.submolt_name)

    def handle_social_subscribe(self, params: Any):

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

        return self._call_api("subscribe_submolt", params.submolt_name, action)

    def handle_social_follow_agent(self, params: Any):

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

        return self._call_api("follow_agent", params.agent_name, action)

    def handle_social_get_feed(self, params: Any):

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

        return self._call_api("get_feed", sort, limit)

    def handle_social_search(self, params: Any):

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

        return self._call_api("search", params.query, limit)
