import sqlite3
import json
from datetime import datetime
from src.settings import settings
from src.utils import log


class Memory:
    def __init__(self):
        self.conn = sqlite3.connect(settings.DB_PATH)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            learnings TEXT,
            plan TEXT,
            actions TEXT,
            conversation_history TEXT,
            has_published_post INTEGER DEFAULT 0,
            has_published_blog INTEGER DEFAULT 0
        )
    """
        )
        try:
            cursor.execute(
                "ALTER TABLE sessions ADD COLUMN has_published_post INTEGER DEFAULT 0"
            )
            log.info("✅ Added column: has_published_post")
        except:
            pass

        try:
            cursor.execute(
                "ALTER TABLE sessions ADD COLUMN has_published_blog INTEGER DEFAULT 0"
            )
            log.info("✅ Added column: has_published_blog")
        except:
            pass
        self.conn.commit()

    def create_session(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (
                timestamp, 
                actions_performed, 
                learnings, 
                next_session_plan, 
                full_context,
                has_published_post,
                has_published_blog
            )
            VALUES (?, ?, ?, ?, ?, 0, 0)
        """,
            (datetime.now().isoformat(), "[]", "", "", "[]"),
        )
        self.conn.commit()
        session_id = cursor.lastrowid
        log.success(f"Session ID created: {session_id}")
        return session_id

    def save_session(
        self,
        summary,
        actions_performed,
        conversation_history,
        current_session_id,
    ):
        log.info("Saving session in database...")

        has_published_post = 0
        has_published_blog = 0

        for action in actions_performed:
            if isinstance(action, dict):
                action_type = action.get("action_type")
                if action_type in ["create_post", "share_link"]:
                    has_published_post = 1
                elif action_type == "write_blog_article":
                    has_published_blog = 1
            elif isinstance(action, str):
                if (
                    "create_post" in action.lower()
                    or "share_link" in action.lower()
                    or "shared blog post" in action.lower()
                ):
                    has_published_post = 1
                if (
                    "blog article" in action.lower()
                    or "write_blog_article" in action.lower()
                ):
                    has_published_blog = 1

        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE sessions 
            SET actions_performed = ?, 
                learnings = ?, 
                next_session_plan = ?, 
                full_context = ?,
                has_published_post = ?,
                has_published_blog = ?
            WHERE id = ?
        """,
            (
                json.dumps(actions_performed),
                summary["learnings"],
                summary["next_session_plan"],
                json.dumps(conversation_history),
                has_published_post,
                has_published_blog,
                current_session_id,
            ),
        )
        self.conn.commit()

        if has_published_post:
            log.info("📝 Session marked: Moltbook post published")
        if has_published_blog:
            log.info("✍️ Session marked: Blog article published")

        log.success("Session saved in database")

    def get_last_session_publication_status(self, current_session_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT has_published_post, has_published_blog
            FROM sessions
            WHERE id < ?
            ORDER BY id DESC
            LIMIT 1
        """,
            ((current_session_id if hasattr(self, "current_session_id") else 999999),),
        )

        result = cursor.fetchone()

        if result:
            return {
                "has_published_post": bool(result[0]),
                "has_published_blog": bool(result[1]),
            }
        return None

    def get_last_session(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT timestamp, actions_performed, learnings, next_session_plan, full_context
            FROM sessions
            ORDER BY id DESC
            LIMIT 1
        """
        )
        row = cursor.fetchone()

        if row:
            return {
                "timestamp": row[0],
                "actions_performed": json.loads(row[1]),
                "learnings": row[2],
                "next_session_plan": row[3],
                "full_context": json.loads(row[4]),
            }
        return None

    def get_session_history(self, limit=5):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT timestamp, learnings, next_session_plan
            FROM sessions
            ORDER BY id DESC
            LIMIT ?
        """,
            (limit,),
        )

        return [
            {"timestamp": row[0], "learnings": row[1], "plan": row[2]}
            for row in cursor.fetchall()
        ]

    def __del__(self):
        self.conn.close()
