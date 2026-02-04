import time
from src.utils import log


class MoltbookActions:
    def create_post(self, app_steps, params: dict):
        if post_creation_attempted:
            error_msg = "Post creation already attempted this session"
            log.warning(error_msg)
            app_steps.actions_performed.append(
                "SKIPPED: Post creation (already attempted)"
            )
            return {"success": False, "error": error_msg}

        post_creation_attempted = True
        submolt = params.get("submolt", "general")

        result = app_steps.api.create_text_post(
            title=params.get("title", ""),
            content=params.get("content", ""),
            submolt=submolt,
        )
        app_steps.last_post_time = time.time()
        if result.get("success"):
            post_id = result.get("id") or result.get("post", {}).get("id")
            post_url = (
                f"https://moltbook.com/m/{submolt}/post/{post_id}" if post_id else "N/A"
            )

            log.success(f"Post created: {params.get('title', '')[:50]}")
            log.info(f"Post URL: {post_url}")

            app_steps.actions_performed.append(
                f"Created post: {params.get('title', '')}"
            )
            app_steps.created_content_urls.append(
                {"type": "post", "title": params.get("title", ""), "url": post_url}
            )
            return {"success": True}
        else:
            error_msg = result.get("error", "Unknown")
            log.error(f"Post failed: {error_msg}")
            app_steps.actions_performed.append(f"FAILED: Create post ({error_msg})")
            return {"success": False, "error": error_msg}

    def comment_on_post(self, params: dict, app_steps):
        post_id = params.get("post_id", "")
        content: str = params.get("content", "")

        if not content or content.strip() == "":
            error_msg = "Comment content is required and cannot be empty"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        if post_id not in app_steps.available_post_ids:
            error_msg = f"Invalid post_id: {post_id} not in available posts"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        result = app_steps.api.add_comment(
            post_id=post_id, content=params.get("content", "")
        )
        app_steps.last_comment_time = time.time()

        if result.get("success"):
            comment_id = result.get("id") or result.get("comment", {}).get("id")
            comment_url = (
                f"https://moltbook.com/post/{post_id}#comment-{comment_id}"
                if comment_id
                else "N/A"
            )

            log.success(f"Commented on post {post_id[:8]}")
            log.info(f"Comment URL: {comment_url}")

            app_steps.actions_performed.append(f"Commented on post {post_id[:8]}")
            app_steps.created_content_urls.append(
                {"type": "comment", "post_id": post_id[:8], "url": comment_url}
            )
            return {"success": True}
        else:
            error_msg = result.get("error", "Unknown")
            log.error(f"Comment failed: {error_msg}")
            return {"success": False, "error": error_msg}

    def reply_to_comment(self, params: dict, app_steps):
        post_id = params.get("post_id", "")
        comment_id = params.get("comment_id", "")
        content: str = params.get("content", "")

        if not content or content.strip() == "":
            error_msg = "Reply content is required and cannot be empty"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        if not post_id or post_id not in app_steps.available_post_ids:
            error_msg = f"Invalid or missing post_id: {post_id}"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        if comment_id not in app_steps.available_comment_ids:
            error_msg = f"Invalid comment_id: {comment_id} not in available comments"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        result = app_steps.api.reply_to_comment(
            post_id=post_id,
            content=params.get("content", ""),
            parent_comment_id=comment_id,
        )
        app_steps.last_comment_time = time.time()
        if result.get("success"):
            reply_id = result.get("id") or result.get("comment", {}).get("id")
            reply_url = (
                f"https://moltbook.com/post/{post_id}#comment-{reply_id}"
                if reply_id
                else "N/A"
            )

            log.success(f"Replied to comment {comment_id[:8]}")
            log.info(f"Reply URL: {reply_url}")

            app_steps.actions_performed.append(f"Replied to comment {comment_id[:8]}")
            app_steps.created_content_urls.append(
                {
                    "type": "reply",
                    "parent_comment_id": comment_id[:8],
                    "url": reply_url,
                }
            )
            return {"success": True}
        else:
            error_msg = result.get("error", "Unknown")
            log.error(f"Reply failed: {error_msg}")
            return {"success": False, "error": error_msg}

    def vote_post(self, params: dict, app_steps):
        post_id = params.get("post_id", "")
        vote_type: str = params.get("vote_type", "upvote")

        if not post_id or post_id not in app_steps.available_post_ids:
            error_msg = f"Invalid or missing post_id: {post_id}"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        result = app_steps.api.vote(
            content_id=post_id, content_type="posts", vote_type=vote_type
        )
        if result.get("success"):
            log.success(f"{vote_type.capitalize()}d post {post_id[:8]}")
            app_steps.actions_performed.append(
                f"{vote_type.capitalize()}d post {post_id[:8]}"
            )
            return {"success": True}
        else:
            error_msg = result.get("error", "Unknown")
            log.error(f"{vote_type.capitalize()} failed: {error_msg}")
            return {"success": False, "error": error_msg}

    def follow_agent(self, params: dict, app_steps):
        agent_name = params.get("agent_name", "")
        follow_type: str = params.get("follow_type", "follow")

        if not agent_name:
            error_msg = "Missing agent_name for follow action"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        result = app_steps.api.follow_agent(agent_name, follow_type)
        if result:
            log.success(f"{follow_type.capitalize()}ed agent {agent_name}")
            app_steps.actions_performed.append(
                f"{follow_type.capitalize()}ed agent {agent_name}"
            )
            return {"success": True}
        else:
            error_msg = f"Failed to {follow_type} agent {agent_name}"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

    def refresh_feed(self, params: dict, app_steps):
        log.info("Refreshing feed...")
        posts_data = app_steps.api.get_posts(
            sort=params.get("sort", "hot"), limit=params.get("limit", 20)
        )
        if not posts_data:
            log.warning("Feed refresh returned no data.")
            return {"success": False, "error": "No posts found. Is the API reachable?"}

        app_steps.available_post_ids = []
        app_steps.available_comment_ids = {}

        app_steps.current_feed = app_steps.get_enriched_feed_context(posts_data)

        feed_update = f"""## FEED REFRESHED

{app_steps.current_feed}

UPDATED POST IDs: {', '.join(app_steps.available_post_ids)}
UPDATED COMMENT IDs: {', '.join(app_steps.available_comment_ids.keys())}
"""

        app_steps.update_system_context(feed_update)

        log.success(
            f"Feed refreshed: {len(app_steps.available_post_ids)} posts, {len(app_steps.available_comment_ids)} comments"
        )
        app_steps.actions_performed.append("Refreshed feed")
        return {"success": True}
