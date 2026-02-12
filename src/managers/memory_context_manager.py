from typing import Dict
from src.settings import settings


class MemoryContextManager:
    def __init__(self, memory_handler):
        self.handler = memory_handler

    def get_home_snippet(self) -> str:
        return self.handler.get_agent_context_snippet()

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:
        last_state = self.handler.get_last_session_state() or {}

        recollection_content = ""
        if result and result.get("success"):
            if "data" in result and result.get("action_type") == "memory_retrieve":
                recollection_content = (
                    f"### 🔮 RECOLLECTED SHARDS\n{result.get('data')}\n\n---\n"
                )

        ctx = [
            "## 🧠 INTERNAL MEMORY SYSTEMS",
            f"{status_msg}" if status_msg else "",
            "---",
            recollection_content,
            f"🎯 **LAST SESSION LEARNINGS**: {last_state.get('learnings', 'N/A')}",
            f"📈 **PREVIOUS PLAN**: {last_state.get('plan', 'N/A')}",
            "",
            "### 📂 AVAILABLE CATEGORIES",
        ]

        cursor = self.handler.conn.cursor()
        cursor.execute(
            "SELECT category, COUNT(*) as cnt FROM memory_entries GROUP BY category"
        )
        counts = {row["category"]: row["cnt"] for row in cursor.fetchall()}

        for cat_name, description in settings.MEMORY_CATEGORIES.items():
            count = counts.get(cat_name, 0)
            ctx.append(f"- **{cat_name.upper()}**: {count} shards")
            ctx.append(f"  _{description}_")

        ctx.append(
            "\n### 🛠️ MEMORY PROTOCOL"
            "\nTo recall shards, use: `memory_retrieve`"
            "\n- **params**: `memory_category` (string), `memory_limit` (int), `memory_order` ('asc'|'desc')"
            "\n"
            "\nTo anchor new memory, use: `memory_store`"
            "\n- **params**: `memory_category` (string), `memory_content` (string)"
            "\n"
            "\n👉 **ACTIONS**: `memory_retrieve` | `memory_store` | `refresh_home`"
        )

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        Params = type("Params", (), {"memory_category": item_id, "memory_limit": 10})
        result = self.handler.handle_retrieve_memory(Params())

        return f"""
# 🎯 RECOLLECTION: {item_id}
{result.get('data', 'No shards found in this sector.')}

---
### 🛠️ ACTIONS
👉 **STORE NEW**: `memory_store(memory_category="{item_id}", memory_content="...")`
👉 **BACK**: `memory_list` to see all categories.

🏠 Use `refresh_home` to return to dashboard.
"""
