import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.settings import settings
from src.utils import log
from src.utils.exceptions import (
    SystemLogicError,
    ResourceNotFoundError,
    FormattingError,
)
from src.handlers.base_handler import BaseHandler
from src.managers.progression_system import ProgressionSystem


class MemoryHandler(BaseHandler):
    def __init__(self, db_path: str = None, test_mode=False):
        self.db_path = db_path or settings.DB_PATH
        self.test_mode = test_mode

        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self._init_tables()
        except sqlite3.OperationalError as e:
            raise SystemLogicError(f"Database initialization failed: {str(e)}")

    def _init_tables(self):

        try:
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
                    type TEXT NOT NULL,
                    title TEXT,
                    data TEXT,
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

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    submolt TEXT DEFAULT 'general',
                    url TEXT,
                    created_at TEXT NOT NULL,
                    session_id INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """
            )

            self.conn.commit()

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_category_date ON memory_entries(category, created_at DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_posts_created ON agent_posts(created_at DESC)"
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_post_id ON agent_posts(post_id)"
            )

            self.conn.commit()

            log.info("ℹ️ Memory system operational.")

        except sqlite3.OperationalError as e:
            raise SystemLogicError(f"Database schema creation failed: {str(e)}")

    def create_session(self) -> int:

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (timestamp, actions_performed, learnings, next_session_plan, full_context) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), "[]", "", "", "[]"),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            raise SystemLogicError(f"Session creation failed: {str(e)}")

    def archive_session(
        self, session_id: int, summary: Dict, history: List, actions: List
    ):

        if not session_id or session_id < 1:
            raise FormattingError(
                message=f"Invalid session_id: {session_id}",
                suggestion="Provide a valid positive session ID.",
            )

        has_post = 1 if any("post" in a.lower() for a in actions) else 0
        has_blog = 1 if any("blog" in a.lower() for a in actions) else 0

        try:
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

            if cursor.rowcount == 0:
                raise ResourceNotFoundError(
                    message=f"Session ID {session_id} not found in database.",
                    suggestion="Check if the session exists or was already archived.",
                )

            self.conn.commit()

        except sqlite3.Error as e:
            raise SystemLogicError(f"Session archiving failed: {str(e)}")

    def handle_memory_store(self, params: Any, session_id: int = None) -> Dict:
        try:
            if isinstance(params, dict):
                category = params.get("memory_category")
                content = params.get("memory_content")
            else:
                category = getattr(params, "memory_category", None)
                content = getattr(params, "memory_content", None)

            if not category:
                raise FormattingError(
                    message="Missing 'memory_category' parameter.",
                    suggestion=f"Specify a category: {', '.join(settings.MEMORY_CATEGORIES.keys())}",
                )

            if category not in settings.MEMORY_CATEGORIES:
                raise ResourceNotFoundError(
                    message=f"Category '{category}' does not exist in the neural map.",
                    suggestion=f"Use one of: {', '.join(settings.MEMORY_CATEGORIES.keys())}",
                )

            if not content or not content.strip():
                raise FormattingError(
                    message="Memory content is empty.",
                    suggestion="Provide meaningful content to store in memory.",
                )

            if len(content.strip()) < 10:
                raise FormattingError(
                    message="Memory content too short (< 10 characters).",
                    suggestion="Provide substantial content worth remembering (at least 10 characters).",
                )

            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO memory_entries (category, content, created_at, session_id) VALUES (?, ?, ?, ?)",
                (category, content, datetime.now().isoformat(), session_id),
            )

            cursor.execute(
                "SELECT COUNT(*) FROM memory_entries WHERE category = ?", (category,)
            )
            count = cursor.fetchone()[0]

            if count > settings.MAX_ENTRIES_PER_CATEGORY:
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

            result_text = f"Memory stored in '{category}' sector ({count}/{settings.MAX_ENTRIES_PER_CATEGORY} entries). Content: {content[:50]}..."

            anti_loop = f"Memory already saved in '{category}'. No need to store it again unless you have NEW information."

            return self.format_success(
                action_name="memory_store",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("memory_store"),
            )

        except Exception as e:
            return self.format_error("memory_store", e)

    def handle_memory_retrieve(self, params: Any) -> Dict:
        try:
            if isinstance(params, dict):
                category = params.get("memory_category")
                limit = params.get("memory_limit", 5)
            else:
                category = getattr(params, "memory_category", None)
                limit = getattr(params, "memory_limit", 5)

            if not category:
                raise FormattingError(
                    message="Missing 'memory_category' parameter.",
                    suggestion=f"Specify a category: {', '.join(settings.MEMORY_CATEGORIES.keys())}",
                )

            if category not in settings.MEMORY_CATEGORIES:
                raise ResourceNotFoundError(
                    message=f"Category '{category}' does not exist.",
                    suggestion=f"Use one of: {', '.join(settings.MEMORY_CATEGORIES.keys())}",
                )

            if limit < 1 or limit > 50:
                raise FormattingError(
                    message=f"Invalid limit: {limit}. Must be between 1-50.",
                    suggestion="Set 'memory_limit' between 1 and 50.",
                )

            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT content, created_at FROM memory_entries WHERE category = ? ORDER BY created_at DESC LIMIT ?",
                (category, limit),
            )
            rows = cursor.fetchall()

            if not rows:
                result_text = f"No memories found in '{category}' sector."
                anti_loop = f"Category '{category}' is empty. You already checked - it's still empty. Store something there first."
            else:
                entries = [
                    f"[{row['created_at'][:10]}] {row['content']}" for row in rows
                ]
                result_text = f"RECOLLECTION FROM '{category.upper()}':\n" + "\n".join(
                    entries
                )
                anti_loop = f"Memories from '{category}' retrieved. You now have this information - no need to retrieve again."

            return self.format_success(
                action_name="memory_retrieve",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("memory_retrieve"),
            )

        except Exception as e:
            return self.format_error("memory_retrieve", e)

    def store_metrics(self, session_id: int, metrics: Dict):

        if not session_id or session_id < 1:
            log.error(f"Invalid session_id for metrics: {session_id}")
            return

        required_keys = ["total", "success", "rejected", "failed", "aborted", "score"]
        missing = [k for k in required_keys if k not in metrics]

        if missing:
            log.error(f"Missing metrics keys: {missing}")
            return

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

        except sqlite3.Error as e:
            log.error(f"❌ Metrics storage failed: {e}")

    def get_agent_context_snippet(self) -> str:

        try:
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

        except sqlite3.Error as e:
            log.error(f"Failed to generate context snippet: {e}")
            return "## 🧠 MEMORY ARCHIVE\n_(unavailable)_\n"

    def get_last_session_state(self) -> Optional[Dict]:

        try:
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

        except sqlite3.Error as e:
            log.error(f"Failed to get last session: {e}")
            return None

    def track_action(
        self,
        platform_id: str,
        action_type: str,
        title: str,
        session_id: int,
        extra_data: Dict = None,
    ):

        if not platform_id or not action_type:
            log.warning("Cannot track action: missing platform_id or action_type")
            return

        try:
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

        except sqlite3.Error as e:
            log.error(f"Failed to track action: {e}")

    def get_my_recent_posts(self, limit: int = 5) -> List[Dict]:

        if limit < 1 or limit > 50:
            limit = 5

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT platform_id, title FROM agent_footprint WHERE type = 'moltbook_post' ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            log.error(f"Failed to get recent posts: {e}")
            return []

    def get_active_master_plan(self) -> Optional[Dict]:
        try:
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
                "milestones": (
                    json.loads(row["milestones"]) if row["milestones"] else []
                ),
                "version": row["version"],
                "last_updated": row["updated_at"],
            }

        except sqlite3.Error as e:
            log.error(f"Failed to get master plan: {e}")
            return None

    def create_or_update_master_plan(
        self, objective: str, strategy: str = None, milestones: List[str] = None
    ) -> bool:

        if not objective or not objective.strip():
            raise FormattingError(
                message="Master plan objective is empty.",
                suggestion="Provide a clear strategic objective for the plan.",
            )

        if len(objective.strip()) < 20:
            raise FormattingError(
                message="Master plan objective too short (< 20 characters).",
                suggestion="Provide a substantial objective describing your strategic goals.",
            )

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

        except sqlite3.Error as e:
            raise SystemLogicError(f"Plan persistence failure: {str(e)}")

    def get_recent_learnings(self, limit: int = 3) -> List[Dict[str, str]]:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, learnings FROM sessions
                WHERE learnings IS NOT NULL
                AND learnings != ''
                AND learnings != 'Initial Session'
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append(
                    {"date": row["timestamp"], "learnings": row["learnings"].strip()}
                )

            return result

        except Exception as e:
            log.error(f"Failed to get recent learnings: {e}")
            return []

    def save_agent_post(
        self,
        post_id: str,
        title: str,
        submolt: str = "general",
        url: str = None,
        session_id: int = None,
    ) -> bool:
        if not post_id or not title:
            log.warning("Cannot save post: missing post_id or title")
            return False

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO agent_posts 
                (post_id, title, submolt, url, created_at, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    title,
                    submolt or "general",
                    url,
                    datetime.now().isoformat(),
                    session_id,
                ),
            )
            self.conn.commit()

            if cursor.rowcount > 0:
                log.success(f"📝 Post saved to memory: '{title}' (ID: {post_id})")
                return True
            else:
                log.debug(f"Post {post_id} already exists in database")
                return False

        except sqlite3.Error as e:
            log.error(f"Failed to save agent post: {e}")
            return False

    def get_agent_posts(self, limit: int = 25) -> List[Dict[str, str]]:

        if limit < 1 or limit > 100:
            limit = 25

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT post_id, title, submolt, url, created_at
                FROM agent_posts
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            posts = []
            for row in cursor.fetchall():
                posts.append(
                    {
                        "post_id": row["post_id"],
                        "title": row["title"],
                        "submolt": row["submolt"],
                        "url": row["url"],
                        "created_at": row["created_at"],
                    }
                )

            return posts

        except sqlite3.Error as e:
            log.error(f"Failed to get agent posts: {e}")
            return []

    def get_agent_post_ids(self, limit: int = 25) -> List[str]:

        if limit < 1 or limit > 100:
            limit = 25

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT post_id FROM agent_posts
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            return [row["post_id"] for row in cursor.fetchall()]

        except sqlite3.Error as e:
            log.error(f"Failed to get agent post IDs: {e}")
            return []

    def is_agent_post(self, post_id: str) -> bool:

        if not post_id:
            return False

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT 1 FROM agent_posts WHERE post_id = ? LIMIT 1", (post_id,)
            )
            return cursor.fetchone() is not None

        except sqlite3.Error as e:
            log.error(f"Failed to check if post is agent's: {e}")
            return False

    def delete_agent_post(self, post_id: str) -> bool:

        if not post_id:
            return False

        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM agent_posts WHERE post_id = ?", (post_id,))
            self.conn.commit()

            if cursor.rowcount > 0:
                log.info(f"🗑️ Post {post_id} removed from memory")
                return True
            return False

        except sqlite3.Error as e:
            log.error(f"Failed to delete agent post: {e}")
            return False

    def __del__(self):
        if hasattr(self, "conn"):
            try:
                self.conn.close()
            except:
                pass
