import re
import requests
from typing import Dict, Any
from src.managers.blog_manager import BlogManager
from src.handlers.base_handler import BaseHandler
from src.handlers.memory_handler import MemoryHandler
from src.utils import log
from src.utils.exceptions import (
    ResourceNotFoundError,
    LazyContentError,
    AccessDeniedError,
    SystemLogicError,
    APICommunicationError,
    FormattingError,
)
from src.managers.progression_system import ProgressionSystem


class BlogHandler(BaseHandler):
    def __init__(self, memory_handler: MemoryHandler, test_mode: bool = False):
        self.test_mode = test_mode
        self.blog_manager = BlogManager(test_mode)
        self.memory_handler = memory_handler

    def _remove_all_hashtags(self, content: str) -> str:
        cleaned = re.sub(r"#\w+", "", content)
        cleaned = re.sub(r" +", " ", cleaned)
        cleaned = "\n".join([line for line in cleaned.splitlines() if line.strip()])
        log.warning("🚫 Hashtags removed to prevent UI styling conflicts.")
        return cleaned.strip()

    def handle_write_blog_article(self, params: Any) -> Dict[str, Any]:
        try:
            if (
                "[INSERT]" in params.content
                or "[TODO]" in params.content
                or "[TBD]" in params.content
            ):
                raise LazyContentError(
                    message="Your article contains technical placeholders ([INSERT], [TODO], [TBD]).",
                    suggestion="Complete the article content fully. Do not leave placeholder tags.",
                )

            if len(params.content.strip()) < 100:
                raise LazyContentError(
                    message="Article content is too short (< 100 characters).",
                    suggestion="Write a complete, substantial article with at least 200-300 words.",
                )

            if not params.title or not params.title.strip():
                raise FormattingError(
                    message="Article title is missing or empty.",
                    suggestion="Provide a clear, descriptive title for your article.",
                )

            if not params.excerpt or not params.excerpt.strip():
                raise FormattingError(
                    message="Article excerpt is missing or empty.",
                    suggestion="Provide a brief excerpt (1-2 sentences) summarizing the article.",
                )

            if not params.image_prompt or not params.image_prompt.strip():
                raise FormattingError(
                    message="Image prompt is missing or empty.",
                    suggestion="Provide a detailed prompt for image generation (e.g., 'abstract art with blue and gold colors').",
                )

            cleaned_content = self._remove_all_hashtags(params.content)

            try:
                html_content = self.blog_manager.format_article_safe(cleaned_content)
            except Exception as e:
                raise FormattingError(
                    message=f"Failed to convert markdown to HTML: {str(e)}",
                    suggestion="Check your markdown syntax. Avoid invalid HTML or special characters.",
                )

            processed_excerpt = (
                (params.excerpt[:252] + "...")
                if len(params.excerpt) > 252
                else params.excerpt
            )

            try:
                result = self.blog_manager.post_article(
                    title=params.title,
                    excerpt=processed_excerpt,
                    content=html_content,
                    image_prompt=params.image_prompt,
                )
            except requests.exceptions.Timeout:
                raise APICommunicationError(
                    message="Blog API request timed out after 30 seconds.",
                    suggestion="Try again. If problem persists, the blog server may be down.",
                    api_name="Blog API",
                )
            except requests.exceptions.ConnectionError:
                raise APICommunicationError(
                    message="Cannot connect to blog server.",
                    suggestion="Check network connection or try again later.",
                    api_name="Blog API",
                )
            except Exception as e:
                raise SystemLogicError(f"Blog API unexpected error: {str(e)}")

            if not result.get("success"):
                error_detail = result.get("error", "Unknown error")
                raise SystemLogicError(f"Blog API Failure: {error_detail}")

            article_url = result.get("url", "")

            result_text = f"""Article '{params.title}' published successfully.
URL: {article_url}

📌 NEXT STEPS TO SHARE YOUR ARTICLE:
1. Use `pin_to_workspace(label='BLOG_URL', content='{article_url}')` to save the URL
2. Navigate to SOCIAL mode: `navigate_to_mode(chosen_mode='SOCIAL')`
3. Share the article: `share_link(title='{params.title}', url_to_share='{article_url}', submolt='general')`

DO NOT write another article now. Follow the steps above to share this one."""

            anti_loop = "Article published. Next: PIN the URL, then NAVIGATE to SOCIAL, then SHARE the link. Do NOT write another article."

            owned_tools_count = len(self.memory_handler.get_owned_tools())
            return self.format_success(
                action_name="write_blog_article",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("write_blog_article"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("write_blog_article", e)

    def handle_review_comment_key_requests(self, params: Any) -> Dict[str, Any]:
        try:
            headers = self._get_headers()
            response = requests.get(
                f"{self.blog_manager.blog_api_url}/auto_approve_keys.php",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 404:
                raise ResourceNotFoundError(
                    message="Key review endpoint not found.",
                    suggestion="This feature may not be enabled on your blog.",
                )

            if response.status_code == 403:
                raise AccessDeniedError(
                    message="Access denied to key review endpoint.",
                    suggestion="Check your API key permissions.",
                )

            if response.status_code != 200:
                raise APICommunicationError(
                    message=f"Server returned HTTP {response.status_code}",
                    suggestion="Try again later or check blog server status.",
                    api_name="Blog API",
                )

            result = response.json()
            pending = result.get("requests", [])

            if not pending:
                result_text = "No pending key requests found. Queue is empty."
                anti_loop = "You just checked - there are ZERO pending requests. Do NOT check again immediately. Move to Email, Social, or Research."
                owned_tools_count = len(self.memory_handler.get_owned_tools())
                return self.format_success(
                    action_name="review_comment_key_requests",
                    result_data=result_text,
                    anti_loop_hint=anti_loop,
                    xp_gained=ProgressionSystem.get_xp_value(
                        "review_comment_key_requests"
                    ),
                    owned_tools_count=owned_tools_count,
                )

            details = "\n".join(
                [f"ID: {r['id']} | User: {r['username']}" for r in pending]
            )

            result_text = f"Found {len(pending)} pending key request(s):\n{details}"
            anti_loop = f"You now have the list of {len(pending)} request(s). Do NOT review again. Approve or reject these IDs, then move on."
            owned_tools_count = len(self.memory_handler.get_owned_tools())
            return self.format_success(
                action_name="review_comment_key_requests",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("review_comment_key_requests"),
            )

        except requests.exceptions.Timeout:
            raise APICommunicationError(
                message="Request timed out while fetching key requests.",
                suggestion="Try again. Server may be slow or down.",
                api_name="Blog API",
            )
        except requests.exceptions.JSONDecodeError:
            raise SystemLogicError("Server returned invalid JSON response.")
        except Exception as e:
            return self.format_error("review_comment_key_requests", e)

    def handle_approve_comment_key(self, params: Any) -> Dict[str, Any]:
        try:
            if not hasattr(params, "request_id") or not params.request_id:
                raise FormattingError(
                    message="Missing 'request_id' parameter.",
                    suggestion="Provide the ID of the key request to approve.",
                )

            result = self._process_key_action(params.request_id, "approve")

            result_text = f"Key request ID '{params.request_id}' has been approved."
            anti_loop = "Approval completed. Do NOT approve the same ID again. If there are more requests, process them. Otherwise, move to another task."

            return self.format_success(
                action_name="approve_comment_key",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("approve_comment_key"),
            )

        except Exception as e:
            return self.format_error("approve_comment_key", e)

    def handle_reject_comment_key(self, params: Any) -> Dict[str, Any]:
        try:
            if not hasattr(params, "request_id") or not params.request_id:
                raise FormattingError(
                    message="Missing 'request_id' parameter.",
                    suggestion="Provide the ID of the key request to reject.",
                )

            result = self._process_key_action(params.request_id, "reject")

            result_text = f"Key request ID '{params.request_id}' has been rejected."
            anti_loop = "Rejection completed. Do NOT reject the same ID again. If there are more requests, process them. Otherwise, move to another task."
            owned_tools_count = len(self.memory_handler.get_owned_tools())
            return self.format_success(
                action_name="reject_comment_key",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("reject_comment_key"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("reject_comment_key", e)

    def handle_review_pending_comments(self, params: Any) -> Dict[str, Any]:
        try:
            limit = getattr(params, "limit", 10)

            if limit < 1 or limit > 50:
                raise FormattingError(
                    message=f"Invalid limit value: {limit}. Must be between 1-50.",
                    suggestion="Set 'limit' parameter between 1 and 50.",
                )

            headers = self._get_headers()
            query = {"limit": limit}

            try:
                response = requests.get(
                    f"{self.blog_manager.blog_api_url}/auto_moderate_comments.php",
                    params=query,
                    headers=headers,
                    timeout=10,
                )
            except requests.exceptions.Timeout:
                raise APICommunicationError(
                    message="Moderation API request timed out.",
                    suggestion="Try again with a smaller limit value.",
                    api_name="Blog Moderation API",
                )

            if response.status_code == 404:
                raise ResourceNotFoundError(
                    message="Moderation endpoint not found.",
                    suggestion="This feature may not be enabled on your blog.",
                )

            if response.status_code != 200:
                raise APICommunicationError(
                    message=f"Moderation endpoint returned HTTP {response.status_code}",
                    suggestion="Try again later or check blog server status.",
                    api_name="Blog Moderation API",
                )

            result = response.json()
            comments = result.get("comments", [])

            if not comments:
                result_text = "Moderation queue is EMPTY. No comments to review."
                anti_loop = "Queue is empty - you just checked. Do NOT review again. Move to Email, Social, or Research immediately."
                owned_tools_count = len(self.memory_handler.get_owned_tools())
                return self.format_success(
                    action_name="review_pending_comments",
                    result_data=result_text,
                    anti_loop_hint=anti_loop,
                    xp_gained=ProgressionSystem.get_xp_value("review_pending_comments"),
                    owned_tools_count=owned_tools_count,
                )

            list_txt = "\n".join(
                [
                    f"ID: {c['id']} | {c['author_name']}: {c['content'][:50]}"
                    for c in comments
                ]
            )

            result_text = f"Found {len(comments)} pending comment(s):\n{list_txt}"
            anti_loop = f"You now have {len(comments)} comment(s) to moderate. Approve them, then move on. Do NOT review again."
            owned_tools_count = len(self.memory_handler.get_owned_tools())
            return self.format_success(
                action_name="review_pending_comments",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("review_pending_comments"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("review_pending_comments", e)

    def handle_approve_comment(self, params: Any) -> Dict[str, Any]:
        try:
            if not hasattr(params, "comment_id_blog") or not params.comment_id_blog:
                raise FormattingError(
                    message="Missing 'comment_id_blog' parameter.",
                    suggestion="Provide the ID of the comment to approve.",
                )

            result = self._process_moderation(params.comment_id_blog, "approve")

            result_text = (
                f"Comment ID '{params.comment_id_blog}' approved successfully."
            )
            anti_loop = "Comment approved. Do NOT approve the same comment again. Process remaining comments or move to another task."
            owned_tools_count = len(self.memory_handler.get_owned_tools())
            return self.format_success(
                action_name="approve_comment",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("approve_comment"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("approve_comment", e)

    def get_latest_articles(self, limit: int = 10) -> Dict[str, Any]:
        try:
            if limit < 1 or limit > 50:
                raise FormattingError(
                    message=f"Invalid limit: {limit}. Must be between 1-50.",
                    suggestion="Set limit between 1 and 50.",
                )

            try:
                response = requests.get(
                    f"{self.blog_manager.blog_api_url}/get_articles.php",
                    params={"limit": limit},
                    headers=self._get_headers(),
                    timeout=10,
                )
            except requests.exceptions.Timeout:
                raise APICommunicationError(
                    message="Request timed out while fetching articles.",
                    suggestion="Try again with a smaller limit.",
                    api_name="Blog API",
                )
            except requests.exceptions.ConnectionError:
                raise APICommunicationError(
                    message="Cannot connect to blog server.",
                    suggestion="Check network connection or try again later.",
                    api_name="Blog API",
                )

            if response.status_code != 200:
                raise APICommunicationError(
                    message=f"Failed to retrieve articles (HTTP {response.status_code})",
                    suggestion="Try again later or check blog server status.",
                    api_name="Blog API",
                )

            articles = response.json().get("articles", [])

            if not articles:
                result_text = "No articles published yet."
                anti_loop = "Blog has zero articles. Write your first article instead of checking again."
                owned_tools_count = len(self.memory_handler.get_owned_tools())
                return self.format_success(
                    action_name="get_latest_articles",
                    result_data=result_text,
                    anti_loop_hint=anti_loop,
                    xp_gained=ProgressionSystem.get_xp_value("get_latest_articles"),
                    owned_tools_count=owned_tools_count,
                )

            formatted = "\n".join([f"• {a['title']} (ID: {a['id']})" for a in articles])

            result_text = f"Found {len(articles)} article(s):\n{formatted}"
            anti_loop = "Article list retrieved. Do NOT fetch again unless you just published a new article."
            owned_tools_count = len(self.memory_handler.get_owned_tools())
            return self.format_success(
                action_name="get_latest_articles",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("get_latest_articles"),
                owned_tools_count=owned_tools_count,
            )

        except Exception as e:
            return self.format_error("get_latest_articles", e)

    def _process_key_action(self, request_id: str, action: str) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_approve_keys.php",
                headers=self._get_headers(),
                json={"request_id": request_id, "action": action},
                timeout=10,
            )
        except requests.exceptions.Timeout:
            raise APICommunicationError(
                message=f"Timeout while trying to {action} key request.",
                suggestion="Try again.",
                api_name="Blog API",
            )

        if response.status_code == 404:
            raise ResourceNotFoundError(
                message=f"Key Request ID '{request_id}' not found or already processed.",
                suggestion="Call 'review_comment_key_requests' to get valid IDs.",
            )

        if response.status_code != 200:
            raise APICommunicationError(
                message=f"Key {action} failed (HTTP {response.status_code})",
                suggestion="Try again or check if the request ID is valid.",
                api_name="Blog API",
            )

        return {"success": True, "data": f"Key {action}d for ID {request_id}"}

    def _process_moderation(self, comment_id: str, action: str) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_moderate_comments.php",
                headers=self._get_headers(),
                json={"comment_id": comment_id, "action": action},
                timeout=10,
            )
        except requests.exceptions.Timeout:
            raise APICommunicationError(
                message=f"Timeout while trying to {action} comment.",
                suggestion="Try again.",
                api_name="Blog Moderation API",
            )

        if response.status_code == 404:
            raise ResourceNotFoundError(
                message=f"Comment ID '{comment_id}' not found or already moderated.",
                suggestion="Call 'review_pending_comments' to get fresh IDs.",
            )

        if response.status_code != 200:
            raise APICommunicationError(
                message=f"Comment {action} failed (HTTP {response.status_code})",
                suggestion="Try again or check if the comment ID is valid.",
                api_name="Blog Moderation API",
            )

        return {"success": True, "data": f"Comment {comment_id} {action}d."}

    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.blog_manager.blog_api_key,
            "Content-Type": "application/json",
            "User-Agent": "GeminiAgent/3.0",
        }
