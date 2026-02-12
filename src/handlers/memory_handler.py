import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.settings import settings
from src.utils import log
from src.utils.exceptions import SystemLogicError, ResourceNotFoundError


class MemoryHandler:
    def __init__(self, db_path: str = None, test_mode=False):
        self.db_path = db_path or settings.DB_PATH
        self.test_mode = test_mode
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                learnings TEXT,
                plan TEXT,
                next_session_plan TEXT,
                actions_performed TEXT,
                conversation_history TEXT,
                full_context TEXT,
                has_published_post INTEGER DEFAULT 0,
                has_published_blog INTEGER DEFAULT 0
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_metrics (
                session_id INTEGER PRIMARY KEY,
                total_actions INTEGER NOT NULL,
                successful_actions INTEGER DEFAULT 0,
                supervisor_rejections INTEGER NOT NULL,
                execution_failures INTEGER NOT NULL,
                aborted_tasks INTEGER DEFAULT 0,
                session_score REAL NOT NULL,
                supervisor_verdict TEXT,
                supervisor_grade TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                session_id INTEGER,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_footprint (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform_id TEXT NOT NULL, 
                type TEXT NOT NULL, -- 'moltbook_post', 'moltbook_comment', 'blog_article'
                title TEXT,
                data TEXT, -- JSON blob for extra context
                created_at TEXT NOT NULL,
                session_id INTEGER,
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
        self.conn.commit()

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_category_date ON memory_entries(category, created_at DESC)"
        )
        self.conn.commit()
        log.info("ℹ️ Memory system operational.")

    def create_session(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (timestamp, actions_performed, learnings, next_session_plan, full_context) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), "[]", "", "", "[]"),
        )
        self.conn.commit()
        return cursor.lastrowid

    def archive_session(
        self, session_id: int, summary: Dict, history: List, actions: List
    ):
        has_post = 1 if any("post" in a.lower() for a in actions) else 0
        has_blog = 1 if any("blog" in a.lower() for a in actions) else 0

        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE sessions 
            SET actions_performed = ?, learnings = ?, next_session_plan = ?, 
                full_context = ?, has_published_post = ?, has_published_blog = ?
            WHERE id = ?
        """,
            (
                json.dumps(actions),
                summary.get("learnings", ""),
                summary.get("next_session_plan", ""),
                json.dumps(history),
                has_post,
                has_blog,
                session_id,
            ),
        )
        self.conn.commit()

    def handle_memory_store(self, params: Any, session_id: int = None) -> Dict:
        if isinstance(params, dict):
            category = params.get("memory_category")
            content = params.get("memory_content")
        else:
            category = params.memory_category
            content = params.memory_content

        if category not in settings.MEMORY_CATEGORIES:
            raise ResourceNotFoundError(
                message=f"Category '{category}' does not exist in the neural map.",
                suggestion=f"Use one of: {', '.join(settings.MEMORY_CATEGORIES.keys())}",
            )

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO memory_entries (category, content, created_at, session_id) VALUES (?, ?, ?, ?)",
                (category, content, datetime.now().isoformat(), session_id),
            )

            cursor.execute(
                "SELECT COUNT(*) FROM memory_entries WHERE category = ?", (category,)
            )
            if cursor.fetchone()[0] > settings.MAX_ENTRIES_PER_CATEGORY:
                cursor.execute(
                    """
                    DELETE FROM memory_entries WHERE id IN (
                        SELECT id FROM memory_entries WHERE category = ? 
                        ORDER BY created_at ASC LIMIT 1
                    )
                """,
                    (category,),
                )

            self.conn.commit()
            return {
                "success": True,
                "data": f"✅ Memory shards stored in {category} sector.",
            }
        except Exception as e:
            raise SystemLogicError(f"Database write failure: {e}")

    def handle_memory_retrieve(self, params: Any) -> Dict:
        if isinstance(params, dict):
            category = params.get("memory_category")
            limit = params.get("memory_limit", 5)
        else:
            category = getattr(params, "memory_category", None)
            limit = getattr(params, "memory_limit", 5)

        if not category:
            return {
                "success": False,
                "error": "No category provided to the neural link.",
            }

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT content, created_at FROM memory_entries WHERE category = ? ORDER BY created_at DESC LIMIT ?",
            (category, limit),
        )
        rows = cursor.fetchall()

        if not rows:
            return {"success": True, "data": f"No memories found in {category}."}

        entries = [f"[{row['created_at'][:10]}] {row['content']}" for row in rows]
        return {
            "success": True,
            "data": f"RECOLLECTION FROM {category}:\n" + "\n".join(entries),
        }

    def store_metrics(self, session_id: int, metrics: Dict):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO session_metrics 
                (session_id, total_actions, successful_actions, supervisor_rejections, 
                 execution_failures, aborted_tasks, session_score, supervisor_verdict, 
                 supervisor_grade, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    metrics["total"],
                    metrics["success"],
                    metrics["rejected"],
                    metrics["failed"],
                    metrics["aborted"],
                    metrics["score"],
                    metrics.get("verdict"),
                    metrics.get("grade"),
                    datetime.now().isoformat(),
                ),
            )
            self.conn.commit()
        except Exception as e:
            log.error(f"❌ Metrics storage failed: {e}")

    def get_agent_context_snippet(self) -> str:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT category, COUNT(*) as cnt FROM memory_entries GROUP BY category"
        )
        counts = {row["category"]: row["cnt"] for row in cursor.fetchall()}

        snippet = "## 🧠 MEMORY ARCHIVE\n"
        for cat, desc in settings.MEMORY_CATEGORIES.items():
            count = counts.get(cat, 0)
            snippet += f"- **{cat}**: {desc} ({count} entries)\n"
        return snippet

    def get_last_session_state(self) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row["id"],
            "plan": row["next_session_plan"],
            "learnings": row["learnings"],
            "has_blog": bool(row["has_published_blog"]),
        }

    def track_action(
        self,
        platform_id: str,
        action_type: str,
        title: str,
        session_id: int,
        extra_data: Dict = None,
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO agent_footprint (platform_id, type, title, data, created_at, session_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                platform_id,
                action_type,
                title,
                json.dumps(extra_data or {}),
                datetime.now().isoformat(),
                session_id,
            ),
        )
        self.conn.commit()
        log.info(f"💾 Footprint saved: {action_type} (ID: {platform_id})")

    def get_my_recent_posts(self, limit: int = 5) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT platform_id, title FROM agent_footprint WHERE type = 'moltbook_post' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_active_master_plan(self) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT objective, strategy, milestones, version, updated_at
            FROM master_plan WHERE is_active = 1
            ORDER BY version DESC LIMIT 1
        """
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "objective": row["objective"],
            "strategy": row["strategy"],
            "milestones": json.loads(row["milestones"]) if row["milestones"] else [],
            "version": row["version"],
            "last_updated": row["updated_at"],
        }

    def create_or_update_master_plan(
        self, objective: str, strategy: str = None, milestones: List[str] = None
    ) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE master_plan SET is_active = 0 WHERE is_active = 1")
            cursor.execute("SELECT MAX(version) FROM master_plan")
            row = cursor.fetchone()
            last_version = row[0] if row and row[0] else 0

            now = datetime.now().isoformat()
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
                    now,
                    now,
                ),
            )

            self.conn.commit()
            log.success(f"✅ Master Plan version {last_version + 1} synchronized.")
            return True
        except Exception as e:
            log.error(f"💥 Plan persistence failure: {e}")
            return False

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()
