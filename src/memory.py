import sqlite3
import json
from datetime import datetime
from src.settings import settings
from src.logger import log


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
                actions_performed TEXT,
                learnings TEXT,
                next_session_plan TEXT,
                full_context TEXT
            )
        """
        )
        self.conn.commit()

    def create_session(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (timestamp, actions_performed, learnings, next_session_plan, full_context)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                datetime.now().isoformat(),
                json.dumps([]),
                "Session in progress...",
                "TBD",
                json.dumps([]),
            ),
        )
        self.conn.commit()

        current_session_id = cursor.lastrowid
        log.info(f"Session ID created: {current_session_id}")

        return current_session_id

    def save_session(
        self,
        summary,
        actions_performed,
        conversation_history,
        current_session_id,
    ):
        log.info("Saving session in database...")
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE sessions 
            SET actions_performed = ?, learnings = ?, next_session_plan = ?, full_context = ?
            WHERE id = ?
        """,
            (
                json.dumps(actions_performed),
                summary["learnings"],
                summary["next_session_plan"],
                json.dumps(conversation_history),
                current_session_id,
            ),
        )
        self.conn.commit()
        log.success("Session saved in database")

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
