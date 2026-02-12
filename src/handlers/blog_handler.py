import re
import requests
from typing import Dict, Any
from src.managers.blog_manager import BlogManager
from src.utils import log
from src.utils.exceptions import (
    ResourceNotFoundError,
    LazyContentError,
    AccessDeniedError,
    SystemLogicError,
)


class BlogHandler:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.blog_manager = BlogManager(test_mode)

    def _remove_all_hashtags(self, content: str) -> str:
        cleaned = re.sub(r"#\w+", "", content)
        cleaned = re.sub(r" +", " ", cleaned)
        cleaned = "\n".join([line for line in cleaned.splitlines() if line.strip()])
        log.warning("🚫 Hashtags removed to prevent UI styling conflicts.")
        return cleaned.strip()

    def handle_write_blog_article(self, params: Any) -> Dict[str, Any]:
        if "[INSERT]" in params.content or "[TODO]" in params.content:
            raise LazyContentError(
                message="Your article contains technical placeholders.",
                suggestion="Complete the article content fully. Do not leave [TODO] or [INSERT] tags.",
            )

        cleaned_content = self._remove_all_hashtags(params.content)
        html_content = self.blog_manager.format_article_safe(cleaned_content)

        result = self.blog_manager.post_article(
            title=params.title,
            excerpt=params.excerpt,
            content=html_content,
            image_prompt=params.image_prompt,
        )

        if not result.get("success"):
            raise SystemLogicError(f"Blog API Failure: {result.get('error')}")

        article_url = result.get("url", "")

        return {
            "success": True,
            "data": f"✅ ARTICLE PUBLISHED\nURL: {article_url}\nNext: Share this link on Moltbook.",
            "url": article_url,
        }

    def handle_share_created_blog_post_url(self, params: Any) -> Dict[str, Any]:
        if (
            not params.share_link_url.startswith(self.blog_manager.blog_base_url)
            and not self.test_mode
        ):
            raise AccessDeniedError(
                message="Security violation: URL origin mismatch.",
                suggestion=f"You can only share articles from {self.blog_manager.blog_base_url}",
            )

        return {
            "success": True,
            "data": f"Article '{params.title}' shared successfully.",
        }

    def handle_review_comment_key_requests(self, params: Any) -> Dict[str, Any]:
        try:
            headers = self._get_headers()
            response = requests.get(
                f"{self.blog_manager.blog_api_url}/auto_approve_keys.php",
                headers=headers,
                timeout=10,
            )

            if response.status_code != 200:
                raise SystemLogicError(f"Server returned HTTP {response.status_code}")

            result = response.json()
            pending = result.get("requests", [])

            if not pending:
                return {"success": True, "data": "No pending key requests found."}

            details = "\n".join(
                [f"ID: {r['id']} | User: {r['username']}" for r in pending]
            )
            return {"success": True, "data": f"PENDING KEYS:\n{details}"}

        except Exception as e:
            raise SystemLogicError(f"Key Review Failed: {str(e)}")

    def handle_approve_comment_key(self, params: Any) -> Dict[str, Any]:
        return self._process_key_action(params.request_id, "approve")

    def handle_reject_comment_key(self, params: Any) -> Dict[str, Any]:
        return self._process_key_action(params.request_id, "reject")

    def handle_review_pending_comments(self, params: Any) -> Dict[str, Any]:
        headers = self._get_headers()
        query = {"limit": params.limit}

        response = requests.get(
            f"{self.blog_manager.blog_api_url}/auto_moderate_comments.php",
            params=query,
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            raise SystemLogicError("Moderation endpoint unreachable.")

        result = response.json()
        comments = result.get("comments", [])

        if not comments:
            return {"success": True, "data": "Moderation queue is empty."}

        list_txt = "\n".join(
            [
                f"ID: {c['id']} | {c['author_name']}: {c['content'][:50]}"
                for c in comments
            ]
        )
        return {"success": True, "data": f"PENDING COMMENTS:\n{list_txt}"}

    def handle_approve_comment(self, params: Any) -> Dict[str, Any]:
        return self._process_moderation(params.comment_id_blog, "approve")

    def get_latest_articles(self, limit: int = 10) -> Dict[str, Any]:
        try:
            response = requests.get(
                f"{self.blog_manager.blog_api_url}/get_articles.php",
                params={"limit": limit},
                headers=self._get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                articles = response.json().get("articles", [])
                if not articles:
                    return {"success": True, "data": "No articles published yet."}

                formatted = "\n".join(
                    [f"• {a['title']} (ID: {a['id']})" for a in articles]
                )
                return {"success": True, "data": formatted, "raw": articles}
            return {"success": False, "data": "Could not retrieve articles."}
        except Exception as e:
            return {"success": False, "data": f"Error: {str(e)}"}

    def _process_key_action(self, request_id: str, action: str):
        response = requests.post(
            f"{self.blog_manager.blog_api_url}/auto_approve_keys.php",
            headers=self._get_headers(),
            json={"request_id": request_id, "action": action},
            timeout=10,
        )
        if response.status_code == 404:
            raise ResourceNotFoundError(
                message=f"Key Request ID '{request_id}' not found.",
                suggestion="Call 'review_comment_key_requests' to refresh valid IDs.",
            )
        return {"success": True, "data": f"Key {action}ed for ID {request_id}"}

    def _process_moderation(self, comment_id: str, action: str):
        response = requests.post(
            f"{self.blog_manager.blog_api_url}/auto_moderate_comments.php",
            headers=self._get_headers(),
            json={"comment_id": comment_id, "action": action},
            timeout=10,
        )
        if response.status_code == 404:
            raise ResourceNotFoundError(
                message=f"Comment ID '{comment_id}' invalid.",
                suggestion="Review the moderation queue to get fresh IDs.",
            )
        return {"success": True, "data": f"Comment {comment_id} {action}ed."}

    def _get_headers(self):
        return {
            "X-API-Key": self.blog_manager.blog_api_key,
            "Content-Type": "application/json",
            "User-Agent": "GeminiAgent/3.0",
        }
