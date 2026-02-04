from src.services.blog_manager import BlogManager
from src.utils import log
import requests


class BlogActions:

    def __init__(self):
        self.blog_manager = BlogManager()

    def write_and_publish_article(self, params: dict, app_steps) -> dict:
        if app_steps.blog_article_attempted:
            error_msg = (
                "Blog article already published this session (limit: 1 per session)"
            )
            log.warning(error_msg)
            app_steps.actions_performed.append(
                "SKIPPED: Blog article creation (already published this session)"
            )
            return {"success": False, "error": error_msg}

        title = params.get("title", "")
        excerpt = params.get("excerpt", "")
        content = params.get("content", "")
        image_prompt = params.get("image_prompt", "")

        if not excerpt and content:
            excerpt = content[:147] + "..."
            log.info("Auto-generated missing excerpt from content.")

        if not image_prompt:
            params["image_prompt"] = (
                f"Cinematic digital art of {params.get('title', 'tech neon cites cyberpunk')}, dark atmosphere, high tech."
            )
            log.info("Auto-generated missing image_prompt.")

        required = ["title", "content", "excerpt", "image_prompt"]
        missing = [p for p in required if not params.get(p)]

        if missing:
            return {
                "success": False,
                "error": f"Missing mandatory fields: {', '.join(missing)}",
            }

        html_content = self.blog_manager.format_article_html(content)

        result = self.blog_manager.post_article(
            title=title,
            excerpt=excerpt,
            content=html_content,
            image_prompt=image_prompt,
        )

        if result.get("success"):
            article_url = result.get("url", "")

            app_steps.actions_performed.append(
                f"Published blog article: '{title}' - {article_url}"
            )

            feedback = f"\n\n## 🎯 BLOG ARTICLE JUST PUBLISHED\n"
            feedback += f"- **Title**: {title}\n"
            feedback += f"- **URL**: {article_url}\n"
            feedback += f"- **Action**: You can now share it on Moltbook with 'share_blog_post'\n"
            feedback += (
                f"- **Limit**: No more articles can be published this session.\n\n"
            )

            app_steps.update_system_context(feedback)

            log.success(f"Blog article published: {title}")
            return result
        else:
            error_msg = result.get("error", "Unknown error")
            log.error(f"Failed to publish article: {error_msg}")
            return result

    def share_blog_post_on_moltbook(self, params: dict, app_steps) -> dict:
        title = params.get("title", "")
        url = params.get("url", "")
        submolt = params.get("submolt", "general")

        if not all([title, url]):
            error_msg = "share_blog_post requires: title, url"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        if not url.startswith(app_steps.blog_manager.blog_base_url):
            error_msg = "URL must be from Coach Brutality's blog"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        response = app_steps.api.create_link_post(
            title=title, url_to_share=url, submolt=submolt
        )

        if response.get("success"):
            post_id = response.get("data", {}).get("id")
            post_url = f"https://www.moltbook.com/posts/{post_id}"

            app_steps.actions_performed.append(
                f"Shared blog article on Moltbook: '{title}' - {post_url}"
            )

            app_steps.created_content_urls.append(post_url)
            app_steps.last_post_time = __import__("time").time()

            log.success(f"🔗 Shared blog post on Moltbook: {title}")
            return {"success": True, "post_url": post_url}
        else:
            error_msg = response.get("error", "Unknown error")
            log.error(f"Failed to share blog post: {error_msg}")
            return {"success": False, "error": error_msg}

    def review_comment_key_requests(self, params: dict, app_steps) -> dict:
        try:
            headers = {
                "X-API-Key": self.blog_manager.blog_api_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }

            response = requests.get(
                f"{self.blog_manager.blog_api_url}/auto_approve_keys.php",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    pending = result.get("requests", [])
                    count = result.get("count", 0)

                    log.success(f"Found {count} pending comment key requests")

                    app_steps.actions_performed.append(
                        f"[FREE] Reviewed {count} comment key requests"
                    )

                    return {"success": True, "count": count, "requests": pending}
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            log.error(f"Failed to review key requests: {e}")
            return {"success": False, "error": str(e)}

    def approve_comment_key(self, params: dict, app_steps) -> dict:
        request_id = params.get("request_id", "")

        if not request_id:
            error_msg = "approve_comment_key requires: request_id"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        try:
            headers = {
                "X-API-Key": self.blog_manager.blog_api_key,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            }

            data = {"request_id": request_id, "action": "approve"}

            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_approve_keys.php",
                headers=headers,
                json=data,
                timeout=10,
            )

            if response.status_code == 404:
                error_msg = f"Request ID '{request_id}' not found. You must use 'review_comment_key_requests' FIRST to see available request IDs before approving."
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    agent_name = result.get("agent_name", "")

                    log.success(f"✅ Approved comment key for: {agent_name}")

                    app_steps.actions_performed.append(
                        f"[FREE] Approved comment key for {agent_name}"
                    )

                    return result
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            log.error(f"Failed to approve key: {e}")
            return {"success": False, "error": str(e)}

    def reject_comment_key(self, params: dict, app_steps) -> dict:
        request_id = params.get("request_id", "")

        if not request_id:
            error_msg = "reject_comment_key requires: request_id"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        try:
            headers = {
                "X-API-Key": self.blog_manager.blog_api_key,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            }

            data = {"request_id": request_id, "action": "reject"}

            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_approve_keys.php",
                headers=headers,
                json=data,
                timeout=10,
            )

            if response.status_code == 404:
                error_msg = f"Request ID '{request_id}' not found. You must use 'review_comment_key_requests' FIRST to see available request IDs before rejecting."
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    agent_name = result.get("agent_name", "")

                    log.warning(f"❌ Rejected comment key for: {agent_name}")

                    app_steps.actions_performed.append(
                        f"[FREE] Rejected comment key for {agent_name}"
                    )

                    return result
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            log.error(f"Failed to reject key: {e}")
            return {"success": False, "error": str(e)}

    def list_articles(self) -> list:
        try:
            headers = {
                "X-API-Key": self.blog_manager.blog_api_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
            url = f"{self.blog_manager.blog_api_url}/get_articles.php"
            log.info(f"Syncing from: {url}")
            response = requests.get(
                url,
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    articles = result.get("articles", [])
                    log.info(
                        f"Successfully retrieved {len(articles)} existing articles."
                    )
                    return articles
                else:
                    log.error(f"API returned error during sync: {result.get('error')}")
                    return []
            else:
                log.error(f"HTTP Error {response.status_code} while fetching articles.")
                return []

        except Exception as e:
            log.error(f"Failed to fetch blog articles list: {e}")
            return []

    def review_pending_comments(self, params: dict, app_steps) -> dict:
        try:
            headers = {
                "X-API-Key": self.blog_manager.blog_api_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }

            query_params = {}
            if params.get("article_id"):
                query_params["article_id"] = params["article_id"]
            if params.get("limit"):
                query_params["limit"] = params["limit"]

            response = requests.get(
                f"{self.blog_manager.blog_api_url}/auto_moderate_comments.php",
                params=query_params,
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    pending = result.get("comments", [])
                    count = result.get("count", 0)

                    log.success(f"📋 Found {count} pending comments")

                    filter_msg = (
                        f" for article {params['article_id']}"
                        if params.get("article_id")
                        else ""
                    )
                    app_steps.actions_performed.append(
                        f"[FREE] Scanned pending comments{filter_msg}"
                    )

                    return {"success": True, "count": count, "comments": pending}
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            log.error(f"Failed to review comments: {e}")
            return {"success": False, "error": str(e)}

    def approve_comment(self, params: dict, app_steps) -> dict:
        comment_id = params.get("comment_id", "")

        if not comment_id:
            error_msg = "approve_comment requires: comment_id"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        try:
            headers = {
                "X-API-Key": self.blog_manager.blog_api_key,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            }

            data = {"comment_id": comment_id, "action": "approve"}

            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_moderate_comments.php",
                headers=headers,
                json=data,
                timeout=10,
            )

            if response.status_code == 404:
                error_msg = f"Comment ID '{comment_id}' not found. You must use 'review_pending_comments' FIRST to see available comment IDs before approving."
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    author = result.get("author_name", "")
                    article = result.get("article_title", "")

                    log.success(f"✅ Approved comment by {author} on '{article}'")

                    app_steps.actions_performed.append(
                        f"[FREE] Approved comment by {author}"
                    )

                    return result
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            log.error(f"Failed to approve comment: {e}")
            return {"success": False, "error": str(e)}

    def reject_comment(self, params: dict, app_steps) -> dict:
        comment_id = params.get("comment_id", "")

        if not comment_id:
            error_msg = "reject_comment requires: comment_id"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        try:
            headers = {
                "X-API-Key": self.blog_manager.blog_api_key,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            }

            data = {"comment_id": comment_id, "action": "reject"}

            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_moderate_comments.php",
                headers=headers,
                json=data,
                timeout=10,
            )

            if response.status_code == 404:
                error_msg = f"Comment ID '{comment_id}' not found. You must use 'review_pending_comments' FIRST to see available comment IDs before rejecting."
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    author = result.get("author_name", "")
                    article = result.get("article_title", "")

                    log.warning(f"❌ Rejected comment by {author} on '{article}'")

                    app_steps.actions_performed.append(
                        f"[FREE] Rejected comment by {author}"
                    )

                    return result
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            log.error(f"Failed to reject comment: {e}")
            return {"success": False, "error": str(e)}
