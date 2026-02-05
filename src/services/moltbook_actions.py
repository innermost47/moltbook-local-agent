import time
import sqlite3
from datetime import datetime
from src.utils import log


class MoltbookActions:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)

    def create_post(self, app_steps, params: dict, post_creation_attempted: bool):
        if post_creation_attempted:
            error_msg = "Post creation already attempted this session"
            app_steps.actions_performed.append(
                "SKIPPED: Post creation (already attempted)"
            )
            return {"success": False, "error": error_msg}

        app_steps.post_creation_attempted = True
        submolt = params.get("submolt", "general")
        title = params.get("title", "")

        result = app_steps.api.create_text_post(
            title=title,
            content=params.get("content", ""),
            submolt=submolt,
        )

        app_steps.last_post_time = time.time()

        if result.get("success"):
            post_id = result.get("id") or result.get("data", {}).get("id")
            post_url = (
                f"https://moltbook.com/m/{submolt}/post/{post_id}"
                if post_id
                else "URL Unavailable"
            )

            log.success(f"Post created: {title[:50]}")

            app_steps.actions_performed.append(f"Created post: {title}")

            app_steps.created_content_urls.append(
                {"type": "post", "title": title, "url": post_url}
            )

            return {
                "success": True,
                "data": f"POST SUCCESSFULLY CREATED:\n- Title: {title}\n- Submolt: m/{submolt}\n- URL: {post_url}\n\nYour content is now visible to other users.",
                "post_url": post_url,
            }
        else:
            error_msg = result.get("error", "Unknown API error")
            app_steps.actions_performed.append(f"FAILED: Create post ({error_msg})")
            return {"success": False, "error": f"Failed to create post: {error_msg}"}

    def post_link(self, app_steps, params: dict):

        submolt = params.get("submolt", "general")
        title = params.get("title", "")
        url_to_share = params.get("url_to_share", "")

        result = app_steps.api.create_link_post(
            title=title,
            url_to_share=url_to_share,
            submolt=submolt,
        )

        if result.get("success"):
            post_data = result.get("data", {})
            post_id = result.get("id") or post_data.get("id")

            post_url = (
                f"https://moltbook.com/m/{submolt}/post/{post_id}"
                if post_id
                else "URL Unavailable"
            )

            log.success(f"Link shared: {title[:50]}")
            log.info(f"Link POST URL: {post_url}")

            app_steps.actions_performed.append(f"Shared link: {title}")

            app_steps.created_content_urls.append(
                {"type": "post_link", "title": title, "url": post_url}
            )

            return {
                "success": True,
                "data": f"LINK POST CREATED:\n- Title: {title}\n- Shared URL: {url_to_share}\n- Moltbook URL: {post_url}\n\nYour link is now live in m/{submolt}.",
                "post_url": post_url,
            }
        else:
            error_msg = result.get("error", "Unknown API error")
            log.error(f"Failed to share link: {error_msg}")
            app_steps.actions_performed.append(f"FAILED: Share link ({error_msg})")

            return {"success": False, "error": f"Link sharing failed: {error_msg}"}

    def comment_on_post(self, params: dict, app_steps):
        post_id = params.get("post_id", "")
        content: str = params.get("content", "")

        if not content or content.strip() == "":
            return {
                "success": False,
                "error": "❌ Protocol Violation: Comment content cannot be empty.",
            }

        if post_id not in app_steps.available_post_ids:
            if post_id in app_steps.available_comment_ids:
                return {
                    "success": False,
                    "error": f"❌ Logic Error: '{post_id}' is a COMMENT_ID. To engage here, use 'reply_to_comment' instead.",
                }

            targets = "\n".join(
                [f"  [FREQ] POST_ID: {pid}" for pid in app_steps.available_post_ids]
            )
            return {
                "success": False,
                "error": f"❌ Target Desync: '{post_id}' is not a valid post identifier.\nValid frequencies:\n{targets}",
            }

        result = app_steps.api.add_comment(post_id=post_id, content=content)

        app_steps.last_comment_time = time.time()

        if result.get("success"):
            comment_id = result.get("id") or result.get("comment", {}).get("id")

            if comment_id:
                app_steps.available_comment_ids[comment_id] = post_id

            comment_url = (
                f"https://moltbook.com/post/{post_id}#comment-{comment_id}"
                if comment_id
                else "N/A"
            )

            log.success(f"Intel deployed: Comment on post {post_id} [^]")

            app_steps.actions_performed.append(f"Commented on post {post_id}")
            app_steps.created_content_urls.append(
                {"type": "comment", "post_id": post_id, "url": comment_url}
            )

            return {
                "success": True,
                "data": f"COMMENT SUCCESSFULLY DEPLOYED:\n- Post ID: {post_id}\n- Comment ID: {comment_id}\n- URL: {comment_url}\n\nYour comment is now live. You can track engagement in the next feed refresh.",
                "comment_id": comment_id,
            }
        else:
            error_msg = result.get("error", "Unknown API error")
            log.error(f"Comment failed: {error_msg}")
            return {"success": False, "error": f"❌ Deployment Failed: {error_msg}"}

    def reply_to_comment(self, params: dict, app_steps):
        post_id = params.get("post_id", "")
        comment_id = params.get("comment_id", "")
        content: str = params.get("content", "")

        if not content or content.strip() == "":
            return {
                "success": False,
                "error": "❌ Protocol Violation: Reply content cannot be empty.",
            }

        if comment_id not in app_steps.available_comment_ids:
            hierarchy = {}
            for cid, pid in app_steps.available_comment_ids.items():
                if pid not in hierarchy:
                    hierarchy[pid] = []
                hierarchy[pid].append(cid)

            error_tree = "\n".join(
                [
                    f"POST: {pid}\n"
                    + "\n".join([f"  └── COMMENT_ID: {cid}" for cid in cids])
                    for pid, cids in hierarchy.items()
                ]
            )
            return {
                "success": False,
                "error": f"❌ Invalid comment_id: '{comment_id}'. Target re-alignment required:\n\n{error_tree}",
            }

        correct_post_id = app_steps.available_comment_ids.get(comment_id)
        if post_id != correct_post_id:
            log.warning(
                f"Vibrational Desync: post_id {post_id} mismatched. Correcting to {correct_post_id} [!]"
            )
            post_id = correct_post_id

        result = app_steps.api.reply_to_comment(
            post_id=post_id,
            content=content,
            parent_comment_id=comment_id,
        )

        app_steps.last_comment_time = time.time()

        if result.get("success"):
            reply_id = result.get("id") or result.get("comment", {}).get("id")

            if reply_id:
                app_steps.available_comment_ids[reply_id] = post_id

            reply_url = (
                f"https://moltbook.com/post/{post_id}#comment-{reply_id}"
                if reply_id
                else "N/A"
            )

            log.success(f"Beta neutralized: Replied to comment {comment_id} [^]")

            app_steps.actions_performed.append(f"Replied to comment {comment_id}")
            app_steps.created_content_urls.append(
                {
                    "type": "reply",
                    "parent_comment_id": comment_id,
                    "url": reply_url,
                }
            )

            return {
                "success": True,
                "data": f"REPLY SUCCESSFULLY DEPLOYED:\n- Parent Comment: {comment_id}\n- New Reply ID: {reply_id}\n- URL: {reply_url}\n\nYour response is now visible in the thread.",
                "reply_id": reply_id,
            }
        else:
            error_msg = result.get("error", "Unknown API error")
            log.error(f"Reply failed: {error_msg}")
            return {"success": False, "error": f"❌ Action Failed: {error_msg}"}

    def vote_post(self, params: dict, app_steps):
        post_id = params.get("post_id", "")
        vote_type: str = params.get("vote_type", "upvote")

        if not post_id or post_id not in app_steps.available_post_ids:
            targets = "\n".join(
                [f"  [TARGET] POST_ID: {pid}" for pid in app_steps.available_post_ids]
            )
            error_msg = (
                f"❌ Target Error: '{post_id}' is not a valid post identifier.\n"
                f"Available targets:\n{targets}\n\n"
            )
            return {"success": False, "error": error_msg}

        v_type = vote_type.lower() if vote_type else "upvote"

        result = app_steps.api.vote(
            content_id=post_id, content_type="posts", vote_type=v_type
        )

        if result.get("success"):
            symbol = "↑" if v_type == "upvote" else "↓"
            log.success(
                f"Frequency adjusted: {v_type.upper()} on post {post_id} [{symbol}]"
            )

            app_steps.actions_performed.append(f"{v_type.capitalize()}d post {post_id}")

            return {
                "success": True,
                "data": f"VOTE REGISTERED: Successfully applied {v_type.upper()} [{symbol}] to post {post_id}.",
                "vote_type": v_type,
                "post_id": post_id,
            }
        else:
            error_msg = result.get("error", "Unknown API error")
            log.error(f"Vote failed: {error_msg}")
            return {"success": False, "error": f"❌ Adjustment Failed: {error_msg}"}

    def follow_agent(self, params: dict, app_steps):
        agent_name = params.get("agent_name", "")
        follow_type: str = params.get("follow_type", "follow")

        if not agent_name:
            error_msg = "❌ Protocol Violation: Missing 'agent_name' for follow/unfollow action."
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        result = app_steps.api.follow_agent(agent_name, follow_type)

        if result.get("success"):
            action_label = "FOLLOWED" if follow_type == "follow" else "UNFOLLOWED"
            icon = "👤+" if follow_type == "follow" else "👤-"

            log.success(f"{icon} Successfully {follow_type}ed agent: {agent_name}")

            app_steps.actions_performed.append(
                f"{follow_type.capitalize()}ed agent {agent_name}"
            )

            return {
                "success": True,
                "data": f"SOCIAL UPDATE: You have successfully {action_label} agent '{agent_name}'. Your social graph has been updated.",
                "agent_name": agent_name,
                "status": follow_type,
            }
        else:
            error_msg = result.get("error", "Unknown API error")
            log.error(f"Social action failed: {error_msg}")
            return {"success": False, "error": f"❌ Social Action Failed: {error_msg}"}

    def refresh_feed(self, params: dict, app_steps):
        log.info("Refreshing feed...")

        posts_data = app_steps.api.get_posts(
            sort=params.get("sort", "hot"), limit=params.get("limit", 20)
        )

        if not posts_data:
            log.warning("Feed refresh returned no data.")
            return {
                "success": False,
                "error": "No posts found. Verify API connectivity or submolt activity.",
            }

        app_steps.available_post_ids = []
        app_steps.available_comment_ids = {}

        enriched_feed = app_steps.get_enriched_feed_context(posts_data)
        app_steps.current_feed = enriched_feed

        feed_update = f"## FEED REFRESHED (Sort: {params.get('sort', 'hot')})\n\n"
        feed_update += enriched_feed
        feed_update += (
            f"\n\nAVAILABLE POST IDs: {', '.join(app_steps.available_post_ids)}"
        )
        feed_update += f"\nAVAILABLE COMMENT IDs: {', '.join(app_steps.available_comment_ids.keys())}"

        log.success(
            f"Feed refreshed: {len(app_steps.available_post_ids)} posts, {len(app_steps.available_comment_ids)} comments"
        )

        app_steps.actions_performed.append("Refreshed feed")

        return {"success": True, "data": feed_update}

    def track_interaction_from_post(self, post_id: str, app_steps):
        post_data = app_steps.api.get_single_post(post_id)
        if post_data and post_data.get("success"):
            agent_name = post_data.get("data", {}).get("author_name")
            if agent_name:
                self.increment_interaction(agent_name)
                log.info(f"[PRO] Interaction recorded for Alpha/Beta: {agent_name}")

    def increment_interaction(self, agent_name: str) -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                UPDATE agent_follows
                SET interaction_count = interaction_count + 1,
                    last_interaction = ?
                WHERE agent_name = ?
                """,
                (now, agent_name),
            )

            if cursor.rowcount == 0:
                log.info(
                    f"[SHOCK] New agent detected: {agent_name}. Immediate archiving."
                )
                cursor.execute(
                    """
                    INSERT INTO agent_follows (agent_name, followed_at, interaction_count, last_interaction, is_currently_following, notes)
                    VALUES (?, ?, 1, ?, 0, 'Agent détecté via interaction feed')
                    """,
                    (agent_name, now, now),
                )

            self.conn.commit()
            log.success(
                f"[^] Increased dominance over {agent_name} (Interaction #{self._get_count(agent_name)})"
            )
            return True

        except Exception as e:
            log.error(f"Failed to perform vibration update for {agent_name}: {e}")
            return False

    def _get_count(self, agent_name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT interaction_count FROM agent_follows WHERE agent_name = ?",
            (agent_name,),
        )
        result = cursor.fetchone()
        return result[0] if result else 0
