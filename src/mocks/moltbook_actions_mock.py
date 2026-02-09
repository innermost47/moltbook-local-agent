from datetime import datetime
import sqlite3
from src.utils import log


class MoltbookActionsMock:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)

    def publish_public_comment(self, params: dict, app_steps):
        log.success(f"🧪 [MOCK] Comment published to {params.get('post_id','')}")
        return {"success": True}

    def create_post(self, app_steps, params: dict, post_creation_attempted: bool):
        log.success(f"🧪 [MOCK] Text post created: {params.get('title','')}")
        return {"success": True, "id": "post-999"}

    def create_link_post(self, title, url_to_share, submolt="tech"):
        log.success(f"🧪 [MOCK] Link post created: {title} -> {url_to_share}")
        return {"success": True, "id": "link-999", "url": url_to_share}

    def vote_post(self, params: dict, app_steps):
        post_id = params.get("post_id", "")
        vote_type: str = params.get("vote_type", "upvote")
        log.success(f"🧪 [MOCK] Voted {vote_type} on {post_id}")
        return {"success": True}

    def follow_agent(self, params: dict, app_steps):
        agent_name = params.get("agent_name", "")
        follow_type = params.get("follow_type", "follow")
        log.success(f"🧪 [MOCK] {follow_type.capitalize()}ing user: {agent_name}")
        return {"success": True}

    def track_interaction_from_post(self, post_id: str, app_steps):
        post_data = app_steps.api.get_single_post(post_id)
        if post_data and post_data.get("success"):
            agent_name = post_data.get("data", {}).get("author_name")
            if agent_name:
                self.increment_interaction(agent_name)
                log.info(f"[PRO] Interaction recorded for: {agent_name}")

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
