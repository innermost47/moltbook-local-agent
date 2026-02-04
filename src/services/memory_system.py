import sqlite3
from datetime import datetime
from typing import List, Dict
from src.settings import settings
from src.utils import log


class MemorySystem:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DB_PATH
        self.conn = sqlite3.connect(self.db_path)
        self._init_memory_tables()

    def _init_memory_tables(self):
        cursor = self.conn.cursor()

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
            CREATE INDEX IF NOT EXISTS idx_category 
            ON memory_entries(category)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_category_date 
            ON memory_entries(category, created_at DESC)
        """
        )

        self.conn.commit()
        log.info("Memory system tables initialized")

    def store_memory(self, category: str, content: str, session_id: int = None) -> Dict:
        if category not in settings.MEMORY_CATEGORIES:
            allowed_str = ", ".join([f"'{c}'" for c in settings.MEMORY_CATEGORIES])
            error_msg = (
                f"❌ SCHEMA VIOLATION: '{category}' is not a valid memory sector.\n"
                f"Available sectors: {allowed_str}.\n"
                f"[!] ACTION: Re-classify your data into one of these existing sectors."
            )
            return {"success": False, "error": error_msg}

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO memory_entries (category, content, created_at, session_id)
                VALUES (?, ?, ?, ?)
            """,
                (category, content, datetime.now().isoformat(), session_id),
            )

            cursor.execute(
                "SELECT COUNT(*) FROM memory_entries WHERE category = ?", (category,)
            )
            count = cursor.fetchone()[0]

            if count > settings.MAX_ENTRIES_PER_CATEGORY:
                to_delete = count - settings.MAX_ENTRIES_PER_CATEGORY
                cursor.execute(
                    """
                    DELETE FROM memory_entries 
                    WHERE id IN (
                        SELECT id FROM memory_entries 
                        WHERE category = ? 
                        ORDER BY created_at ASC 
                        LIMIT ?
                    )
                """,
                    (category, to_delete),
                )
                log.info(
                    f"Auto-cleanup: removed {to_delete} old entries from '{category}'"
                )

            self.conn.commit()
            return {"success": True}

        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

    def retrieve_memory(
        self,
        category: str,
        limit: int = 5,
        order: str = "desc",
        from_date: str = None,
        to_date: str = None,
    ) -> Dict:
        if category not in settings.MEMORY_CATEGORIES:
            valid_cats = ", ".join([f"'{c}'" for c in settings.MEMORY_CATEGORIES])
            error_msg = (
                f"Invalid category: '{category}'.\n"
                f"Available categories in system settings: {valid_cats}.\n"
                "Please use one of the predefined categories above."
            )

            log.error(error_msg)
            return {"success": False, "error": error_msg}

        try:
            cursor = self.conn.cursor()

            query = "SELECT content, created_at FROM memory_entries WHERE category = ?"
            params = [category]

            if from_date:
                query += " AND created_at >= ?"
                params.append(from_date)

            if to_date:
                query += " AND created_at <= ?"
                params.append(to_date)

            order_clause = "DESC" if order.lower() == "desc" else "ASC"
            query += f" ORDER BY created_at {order_clause} LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            entries = [{"content": row[0], "created_at": row[1]} for row in results]

            log.info(f"Retrieved {len(entries)} memories from '{category}'")
            return {"success": True, "entries": entries}

        except Exception as e:
            error_msg = f"Failed to retrieve memory: {str(e)}"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_category_stats(self, category: str = None) -> Dict:
        try:
            cursor = self.conn.cursor()

            if category:
                if category not in settings.MEMORY_CATEGORIES:
                    return {}

                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as count,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest
                    FROM memory_entries
                    WHERE category = ?
                """,
                    (category,),
                )

                result = cursor.fetchone()

                if result[0] == 0:
                    return {"count": 0, "oldest": None, "newest": None}

                return {"count": result[0], "oldest": result[1], "newest": result[2]}
            else:
                stats = {}

                for cat in settings.MEMORY_CATEGORIES.keys():
                    cursor.execute(
                        """
                        SELECT 
                            COUNT(*) as count,
                            MIN(created_at) as oldest,
                            MAX(created_at) as newest
                        FROM memory_entries
                        WHERE category = ?
                    """,
                        (cat,),
                    )

                    result = cursor.fetchone()

                    if result[0] > 0:
                        stats[cat] = {
                            "count": result[0],
                            "oldest": result[1],
                            "newest": result[2],
                        }

                return stats

        except Exception as e:
            log.error(f"Failed to get category stats: {e}")
            return {}

    def list_categories(self) -> Dict[str, Dict]:
        all_stats = self.get_category_stats()

        result = {}
        for category, description in settings.MEMORY_CATEGORIES.items():
            result[category] = {
                "description": description,
                "stats": all_stats.get(
                    category, {"count": 0, "oldest": None, "newest": None}
                ),
            }

        return result

    def get_memory_context_for_agent(self) -> str:
        categories_info = self.list_categories()

        context = "## MEMORY SYSTEM AVAILABLE\n\n"
        context += "You have access to a categorized memory system (actions are FREE - don't count toward MAX_ACTIONS):\n\n"
        context += "**Available Categories:**\n"

        for category, info in categories_info.items():
            stats = info["stats"]
            if stats["count"] > 0:
                context += f"- **{category}** ({stats['count']} entries, from {stats['oldest'][:10]} to {stats['newest'][:10]})\n"
            else:
                context += f"- **{category}** (empty)\n"

        context += "\n**Memory Actions (FREE):**\n"
        context += "- memory_store: Save information to a category (params: category, content)\n"
        context += "- memory_retrieve: Get entries from a category (params: category, limit, order: 'desc'/'asc', optional: from_date, to_date)\n"
        context += "- memory_list: See all categories with descriptions and stats\n"
        context += "\n**Strategy:** Use memory to track patterns, remember key interactions, and build knowledge over time.\n"

        return context

    def store(self, params: dict, current_session_id: str, actions_performed: List):
        category = params.get("memory_category", "")
        content = params.get("memory_content", "")

        if not category or not content:
            return {
                "success": False,
                "error": "Missing 'memory_category' or 'memory_content'",
            }

        result = self.store_memory(
            category=category, content=content, session_id=current_session_id
        )

        if result["success"]:
            log.success(f"Stored memory in '{category}'")
            actions_performed.append(f"[FREE] Stored memory in '{category}'")
            return {"success": True}
        else:
            log.error(f"Failed to store memory: {result['error']}")
            return result

    def retrieve(self, params: dict, actions_performed: List, update_system_context):
        category = params.get("memory_category", "")
        limit = params.get("memory_limit", 5)
        order = params.get("memory_order", "desc")
        from_date = params.get("from_date")
        to_date = params.get("to_date")

        recent_retrieves = [
            a for a in actions_performed[-3:] if f"Retrieved" in a and category in a
        ]

        if len(recent_retrieves) > 0:
            warning = f"⚠️ You already retrieved '{category}' memories recently. Results are already in your context."
            log.warning(warning)
            return {"success": False, "error": warning}

        if not category:
            error_msg = "Missing category for memory_retrieve"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        result = self.retrieve_memory(
            category=category,
            limit=limit,
            order=order,
            from_date=from_date,
            to_date=to_date,
        )

        if not result["success"]:
            return result

        entries = result["entries"]
        if entries:
            feedback = f"\n## 📚 MEMORIES RETRIEVED FROM '{category}'\n\n"
            for memory in entries:
                feedback += f"- {memory['content'][:100]}...\n"
            feedback += f"\n✅ You now have this information. DO NOT retrieve the same category again.\n"

            update_system_context(feedback)

            log.success(f"📖 Retrieved {len(entries)} memories from '{category}'")
            actions_performed.append(
                f"[FREE] Retrieved {len(entries)} memories from '{category}'"
            )
            return {"success": True}
        else:
            msg = f"No memories found in '{category}'."
            log.info(msg)
            return {"success": True, "message": msg}

    def list(self, update_system_context, actions_performed: List):
        categories_info = self.list_categories()

        list_text = "\n\n## MEMORY CATEGORIES STATUS:\n\n"
        for category, info in categories_info.items():
            stats = info["stats"]
            if stats["count"] > 0:
                list_text += f"- **{category}**: {stats['count']} entries ({stats['oldest'][:10]} to {stats['newest'][:10]})\n"
            else:
                list_text += f"- **{category}**: empty\n"

        update_system_context(list_text)

        log.success("📋 Listed all memory categories")
        actions_performed.append("[FREE] Listed memory categories")

        return {"success": True}

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()
