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
            image_prompt = f"Cinematic digital art of {title or 'tech neon cites cyberpunk'}, dark atmosphere, high tech."
            log.info("Auto-generated missing image_prompt.")

        required = ["title", "content"]
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
            app_steps.blog_article_attempted = True

            app_steps.actions_performed.append(
                f"Published blog article: '{title}' - {article_url}"
            )

            feedback = f"""✅ SUCCESSFULLY PUBLISHED ARTICLE:
- Title: {title}
- URL: {article_url}

🛑 IMPORTANT: You have reached the limit for 'write_blog_article' this session.
🎯 MANDATORY NEXT STEP: Your next action MUST be to share this article on Moltbook using 'share_blog_post'. 
This is critical to ensure visibility and drive traffic to your research.
- URL to use: {article_url}
- Recommended Title: {title}"""

            log.success(f"Blog article published: {title}")

            return {"success": True, "data": feedback, "url": article_url}
        else:
            error_msg = result.get("error", "Unknown error")
            log.error(f"Failed to publish article: {error_msg}")
            return {"success": False, "error": error_msg}

    def share_blog_post_on_moltbook(self, params: dict, app_steps) -> dict:
        title = params.get("title", "")
        url = params.get("share_link_url", "")
        submolt = params.get("submolt", "general")

        if not all([title, url]):
            error_msg = "share_blog_post requires: title, share_link_url"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        if not url.startswith(self.blog_manager.blog_base_url):
            error_msg = f"Security error: URL must be from the official blog ({app_steps.blog_manager.blog_base_url})"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        response = app_steps.api.create_link_post(
            title=title, url_to_share=url, submolt=submolt
        )

        if response.get("success"):
            post_data = response.get("data", {})
            post_id = post_data.get("id")
            post_url = f"https://www.moltbook.com/posts/{post_id}"

            app_steps.actions_performed.append(
                f"Shared blog article on Moltbook: '{title}' - {post_url}"
            )

            app_steps.created_content_urls.append(
                {"type": "blog_shared", "title": title, "url": post_url}
            )
            app_steps.last_post_time = __import__("time").time()

            log.success(f"🔗 Shared blog post on Moltbook: {title}")

            return {
                "success": True,
                "data": f"SUCCESSFULLY SHARED ON MOLTBOOK:\n- Title: {title}\n- Submolt: r/{submolt}\n- Moltbook URL: {post_url}\n\nYour article is now live and visible to the community.",
                "post_url": post_url,
            }
        else:
            error_msg = response.get("error", "Unknown error")
            log.error(f"Failed to share blog post: {error_msg}")
            return {"success": False, "error": f"API Error: {error_msg}"}

    def review_comment_key_requests(self, app_steps) -> dict:
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

                    if count > 0:
                        request_details = "\n".join(
                            [
                                f"- Request ID: {r.get('id')} | User: {r.get('username')} | Reason: {r.get('reason', 'N/A')}"
                                for r in pending
                            ]
                        )
                        data_feedback = f"PENDING KEY REQUESTS ({count}):\n{request_details}\n\nYou can now approve or reject them using the appropriate action."
                    else:
                        data_feedback = (
                            "No pending comment key requests found at the moment."
                        )

                    app_steps.actions_performed.append(
                        f"[BLOG] Reviewed {count} comment key requests"
                    )

                    return {"success": True, "data": data_feedback, "count": count}
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code} - Server unreachable",
                }

        except Exception as e:
            log.error(f"Failed to review key requests: {e}")

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

            payload = {"request_id": request_id, "action": "approve"}

            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_approve_keys.php",
                headers=headers,
                json=payload,
                timeout=10,
            )

            if response.status_code == 404:
                error_msg = f"Request ID '{request_id}' not found. Ensure you are using an ID from the latest 'review_comment_key_requests' call."
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    agent_name = result.get("agent_name", "Unknown Agent")

                    log.success(f"✅ Approved comment key for: {agent_name}")

                    app_steps.actions_performed.append(
                        f"[BLOG] Approved comment key for {agent_name}"
                    )

                    return {
                        "success": True,
                        "data": f"KEY APPROVED: The request {request_id} for agent '{agent_name}' has been successfully processed. They now have access to comment.",
                        "agent_name": agent_name,
                    }
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code} - Server error during approval",
                }

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

            payload = {"request_id": request_id, "action": "reject"}

            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_approve_keys.php",
                headers=headers,
                json=payload,
                timeout=10,
            )

            if response.status_code == 404:
                error_msg = f"Request ID '{request_id}' not found. Make sure to call 'review_comment_key_requests' to get valid IDs."
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    agent_name = result.get("agent_name", "Unknown Agent")

                    log.warning(f"❌ Rejected comment key for: {agent_name}")

                    app_steps.actions_performed.append(
                        f"[BLOG] Rejected comment key for {agent_name}"
                    )

                    return {
                        "success": True,
                        "data": f"KEY REJECTED: Request {request_id} for agent '{agent_name}' has been successfully rejected and removed from the queue.",
                        "agent_name": agent_name,
                    }
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code} - Rejection failed",
                }

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

                    if count > 0:
                        comments_list = ""
                        for c in pending:
                            comments_list += f"- ID: {c.get('id')} | Author: {c.get('author_name')} | Content: \"{c.get('content')}\"\n"

                        data_feedback = f"PENDING COMMENTS QUEUE ({count}):\n{comments_list}\nUse 'moderate_comment' with 'action': 'approve' or 'reject' for these IDs."
                    else:
                        data_feedback = "The pending comments queue is currently empty."

                    filter_msg = (
                        f" for article {params['article_id']}"
                        if params.get("article_id")
                        else ""
                    )
                    app_steps.actions_performed.append(
                        f"[BLOG] Scanned pending comments{filter_msg}"
                    )

                    return {"success": True, "data": data_feedback, "count": count}
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code} - Could not reach moderation endpoint",
                }

        except Exception as e:
            log.error(f"Failed to review comments: {e}")
            return {"success": False, "error": str(e)}

    def approve_comment(self, params: dict, app_steps) -> dict:
        comment_id = params.get("comment_id", "")

        if not comment_id:
            return {"success": False, "error": "approve_comment requires: comment_id"}

        try:
            headers = {
                "X-API-Key": self.blog_manager.blog_api_key,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            }

            payload = {"comment_id": comment_id, "action": "approve"}

            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_moderate_comments.php",
                headers=headers,
                json=payload,
                timeout=10,
            )

            if response.status_code == 404:
                error_msg = f"Comment ID '{comment_id}' not found. Use 'review_pending_comments' to refresh the queue."
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    author = result.get("author_name", "Unknown")
                    article = result.get("article_title", "Unknown Article")

                    log.success(f"✅ Approved comment by {author} on '{article}'")
                    app_steps.actions_performed.append(
                        f"[BLOG] Approved comment by {author}"
                    )

                    return {
                        "success": True,
                        "data": f"COMMENT APPROVED: ID {comment_id} by {author} on article '{article}' is now public.",
                        "author": author,
                    }
                return {"success": False, "error": result.get("error")}
            return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            log.error(f"Failed to approve comment: {e}")
            return {"success": False, "error": str(e)}

    def reject_comment(self, params: dict, app_steps) -> dict:
        comment_id = params.get("comment_id", "")

        if not comment_id:
            return {"success": False, "error": "reject_comment requires: comment_id"}

        try:
            headers = {
                "X-API-Key": self.blog_manager.blog_api_key,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            }

            payload = {"comment_id": comment_id, "action": "reject"}

            response = requests.post(
                f"{self.blog_manager.blog_api_url}/auto_moderate_comments.php",
                headers=headers,
                json=payload,
                timeout=10,
            )

            if response.status_code == 404:
                error_msg = f"Comment ID '{comment_id}' not found. Review the queue again to see updated IDs."
                log.error(error_msg)
                return {"success": False, "error": error_msg}

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    author = result.get("author_name", "Unknown")

                    log.warning(f"❌ Rejected comment by {author}")
                    app_steps.actions_performed.append(
                        f"[BLOG] Rejected comment by {author}"
                    )

                    return {
                        "success": True,
                        "data": f"COMMENT REJECTED: ID {comment_id} by {author} has been removed from the queue.",
                        "author": author,
                    }
                return {"success": False, "error": result.get("error")}
            return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            log.error(f"Failed to reject comment: {e}")
            return {"success": False, "error": str(e)}
