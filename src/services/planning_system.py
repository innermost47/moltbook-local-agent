import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from src.utils import log


class PlanningSystem:

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._init_planning_tables()

    def _init_planning_tables(self):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_follows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL UNIQUE,
                followed_at TEXT NOT NULL,
                unfollowed_at TEXT,
                is_currently_following BOOLEAN DEFAULT 1,
                interaction_count INTEGER DEFAULT 0,
                last_interaction TEXT,
                notes TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                task TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                priority INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS master_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                objective TEXT NOT NULL,
                strategy TEXT,
                milestones TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_follows_current 
            ON agent_follows(is_currently_following, agent_name)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_todos_session 
            ON session_todos(session_id, status)
        """
        )

        self.conn.commit()
        log.info("Planning system tables initialized")

    def get_active_master_plan(self) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT objective, strategy, milestones, version, updated_at
            FROM master_plan
            WHERE is_active = 1
            ORDER BY version DESC
            LIMIT 1
        """
        )

        result = cursor.fetchone()
        if not result:
            return None

        return {
            "objective": result[0],
            "strategy": result[1],
            "milestones": json.loads(result[2]) if result[2] else [],
            "version": result[3],
            "last_updated": result[4],
        }

    def create_or_update_master_plan(
        self, objective: str, strategy: str = None, milestones: List[str] = None
    ) -> bool:
        try:
            cursor = self.conn.cursor()

            cursor.execute("UPDATE master_plan SET is_active = 0 WHERE is_active = 1")

            cursor.execute("SELECT MAX(version) FROM master_plan")
            last_version = cursor.fetchone()[0] or 0

            cursor.execute(
                """
                INSERT INTO master_plan (version, objective, strategy, milestones, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
                (
                    last_version + 1,
                    objective,
                    strategy,
                    json.dumps(milestones) if milestones else None,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )

            self.conn.commit()
            log.success(f"Master plan updated to version {last_version + 1}")
            return True

        except Exception as e:
            log.error(f"Failed to update master plan: {e}")
            return False

    def get_master_plan_history(self, limit: int = 5) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT version, objective, strategy, created_at, is_active
            FROM master_plan
            ORDER BY version DESC
            LIMIT ?
        """,
            (limit,),
        )

        results = cursor.fetchall()
        return [
            {
                "version": row[0],
                "objective": row[1],
                "strategy": row[2],
                "created_at": row[3],
                "is_active": bool(row[4]),
            }
            for row in results
        ]

    def create_session_todos(self, session_id: int, tasks: List[Dict]) -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()

            for task_data in tasks:
                cursor.execute(
                    """
                    INSERT INTO session_todos (session_id, task, priority, created_at, status)
                    VALUES (?, ?, ?, ?, 'pending')
                """,
                    (
                        session_id,
                        task_data.get("task"),
                        task_data.get("priority", 0),
                        now,
                    ),
                )

            self.conn.commit()
            log.success(f"Created {len(tasks)} todos for session {session_id}")
            return True

        except Exception as e:
            log.error(f"Failed to create todos: {e}")
            return False

    def get_session_todos(self, session_id: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, task, status, priority, created_at, completed_at
            FROM session_todos
            WHERE session_id = ?
            ORDER BY priority DESC, created_at ASC
        """,
            (session_id,),
        )

        results = cursor.fetchall()
        return [
            {
                "id": row[0],
                "task": row[1],
                "status": row[2],
                "priority": row[3],
                "created_at": row[4],
                "completed_at": row[5],
            }
            for row in results
        ]

    def get_last_session_todos(
        self, exclude_session_id: int = None
    ) -> Optional[List[Dict]]:
        cursor = self.conn.cursor()

        query = """
            SELECT session_id
            FROM session_todos
        """

        if exclude_session_id:
            query += " WHERE session_id != ?"
            cursor.execute(
                query + " ORDER BY session_id DESC LIMIT 1", (exclude_session_id,)
            )
        else:
            cursor.execute(query + " ORDER BY session_id DESC LIMIT 1")

        result = cursor.fetchone()
        if not result:
            return None

        return self.get_session_todos(result[0])

    def update_todo_status(
        self, todo_id: int, status: str, completed_at: str = None
    ) -> bool:
        try:
            cursor = self.conn.cursor()

            if status == "completed" and not completed_at:
                completed_at = datetime.now().isoformat()

            cursor.execute(
                """
                UPDATE session_todos
                SET status = ?, completed_at = ?
                WHERE id = ?
            """,
                (status, completed_at, todo_id),
            )

            self.conn.commit()
            log.success(f"Todo {todo_id} marked as {status}")
            return True

        except Exception as e:
            log.error(f"Failed to update todo status: {e}")
            return False

    def record_follow(self, agent_name: str, notes: str = None) -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                SELECT id, is_currently_following FROM agent_follows WHERE agent_name = ?
            """,
                (agent_name,),
            )

            result = cursor.fetchone()

            if result:
                if not result[1]:
                    cursor.execute(
                        """
                        UPDATE agent_follows
                        SET is_currently_following = 1,
                            followed_at = ?,
                            unfollowed_at = NULL,
                            notes = ?
                        WHERE agent_name = ?
                    """,
                        (now, notes, agent_name),
                    )
                else:
                    log.info(f"Agent {agent_name} is already followed")
                    return True
            else:
                cursor.execute(
                    """
                    INSERT INTO agent_follows (agent_name, followed_at, notes, is_currently_following)
                    VALUES (?, ?, ?, 1)
                """,
                    (agent_name, now, notes),
                )

            self.conn.commit()
            log.success(f"Recorded follow of {agent_name}")
            return True

        except Exception as e:
            log.error(f"Failed to record follow: {e}")
            return False

    def record_unfollow(self, agent_name: str) -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                UPDATE agent_follows
                SET is_currently_following = 0,
                    unfollowed_at = ?
                WHERE agent_name = ? AND is_currently_following = 1
            """,
                (now, agent_name),
            )

            if cursor.rowcount == 0:
                log.warning(f"Agent {agent_name} was not being followed")
                return False

            self.conn.commit()
            log.success(f"Recorded unfollow of {agent_name}")
            return True

        except Exception as e:
            log.error(f"Failed to record unfollow: {e}")
            return False

    def get_currently_following(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT agent_name, followed_at, interaction_count, last_interaction, notes
            FROM agent_follows
            WHERE is_currently_following = 1
            ORDER BY followed_at DESC
        """
        )

        results = cursor.fetchall()
        return [
            {
                "agent_name": row[0],
                "followed_at": row[1],
                "interaction_count": row[2],
                "last_interaction": row[3],
                "notes": row[4],
            }
            for row in results
        ]

    def get_follow_history(self, limit: int = 20) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT agent_name, followed_at, unfollowed_at, is_currently_following, 
                   interaction_count, notes
            FROM agent_follows
            ORDER BY followed_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        results = cursor.fetchall()
        return [
            {
                "agent_name": row[0],
                "followed_at": row[1],
                "unfollowed_at": row[2],
                "currently_following": bool(row[3]),
                "interaction_count": row[4],
                "notes": row[5],
            }
            for row in results
        ]

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

            self.conn.commit()
            return True

        except Exception as e:
            log.error(f"Failed to increment interaction: {e}")
            return False

    def get_planning_context(self) -> str:
        context = ""

        master_plan = self.get_active_master_plan()
        if master_plan:
            context += "## 🎯 YOUR MASTER PLAN\n\n"
            context += f"**Objective (v{master_plan['version']}):** {master_plan['objective']}\n"
            if master_plan["strategy"]:
                context += f"**Strategy:** {master_plan['strategy']}\n"
            if master_plan["milestones"]:
                context += "**Milestones:**\n"
                for i, milestone in enumerate(master_plan["milestones"], 1):
                    context += f"  {i}. {milestone}\n"
            context += f"**Last Updated:** {master_plan['last_updated'][:10]}\n\n"
            context += f"\n\n---  \n\n"
        else:
            context += "## 🎯 NO MASTER PLAN YET\n\n"
            context += (
                "You will create your master plan at the start of this session.\n"
            )
            context += f"\n\n---  \n\n"

        following = self.get_currently_following()
        if following:
            context += f"## 👥 CURRENTLY FOLLOWING ({len(following)} agents)\n\n"
            for agent in following[:10]:
                context += f"- **{agent['agent_name']}**"
                if agent["notes"]:
                    context += f" - {agent['notes']}"
                if agent["interaction_count"] > 0:
                    context += f" ({agent['interaction_count']} interactions)"
                context += "\n"
            if len(following) > 10:
                context += f"... and {len(following) - 10} more\n"
            context += f"\n\n---  \n\n"

        return context

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()
