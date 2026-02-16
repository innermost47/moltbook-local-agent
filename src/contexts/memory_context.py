from typing import Dict
from argparse import Namespace
from src.settings import settings
from src.utils import log
from src.contexts.base_context import BaseContext


class MemoryContext(BaseContext):
    def __init__(self, memory_handler):
        self.handler = memory_handler

    def get_home_snippet(self) -> str:
        try:
            return self.handler.get_agent_context_snippet()
        except Exception as e:
            log.warning(f"Memory snippet generation failed: {e}")
            return "🧠 **MEMORY**: Status unavailable"

    def get_list_view(
        self, status_msg: str = "", result: Dict = None, workspace_pins=None
    ) -> str:
        owned_tools = set(self.handler.get_owned_tools())
        last_state_info = ""
        try:
            last_state = self.handler.get_last_session_state() or {}
            last_state_info = f"""
### 📜 PREVIOUS SESSION STATE

🎯 **Last Learnings**: {last_state.get('learnings', 'N/A')}
📈 **Previous Plan**: {last_state.get('plan', 'N/A')}
"""
        except Exception as e:
            log.warning(f"Could not fetch last session state: {e}")
            last_state_info = "### 📜 PREVIOUS SESSION STATE\n\n_Status unavailable_\n"

        categories_display = ""
        try:
            cursor = self.handler.conn.cursor()
            cursor.execute(
                "SELECT category, COUNT(*) as cnt FROM memory_entries GROUP BY category"
            )
            counts = {row["category"]: row["cnt"] for row in cursor.fetchall()}

            categories_display = "### 📂 AVAILABLE CATEGORIES\n\n"

            for cat_name, description in settings.MEMORY_CATEGORIES.items():
                count = counts.get(cat_name, 0)
                categories_display += f"- **{cat_name.upper()}**: {count} shards\n"
                categories_display += f"  _{description}_\n"
        except Exception as e:
            log.warning(f"Could not fetch memory categories: {e}")
            categories_display = "### 📂 AVAILABLE CATEGORIES\n\n_Status unavailable_\n"

        available_actions = []
        locked_actions = []

        if "pin_to_workspace" in owned_tools:
            available_actions.append(
                """
👉 `pin_to_workspace(label='...', content='...')`
   - Pin important info to workspace (visible everywhere)
   - FREE starter tool
"""
            )

        if "memory_retrieve" in owned_tools:
            available_actions.append(
                """
👉 `memory_retrieve(memory_category='...', memory_limit=10)`
   - Recall stored memories from a category
   - params: category, limit, order ('asc'|'desc')
"""
            )
        else:
            locked_actions.append(
                "🔒 `memory_retrieve` - 100 XP (unlock to read memories)"
            )

        if "memory_store" in owned_tools:
            available_actions.append(
                """
👉 `memory_store(memory_category='...', memory_content='...')`
   - Store new insights in a category
   - Available categories: """
                + ", ".join(settings.MEMORY_CATEGORIES.keys())
            )
        else:
            locked_actions.append(
                "🔒 `memory_store` - 100 XP (unlock to save memories)"
            )

        actions_section = "### 🛠️ MEMORY ACTIONS\n\n"

        if available_actions:
            actions_section += "You are in MEMORY mode. Execute one of these:\n\n"
            actions_section += "\n".join(available_actions)
        else:
            actions_section += "⚠️ **NO MEMORY TOOLS UNLOCKED**\n\n"
            actions_section += (
                "You can view categories, but can't interact with memories yet.\n"
            )

        if locked_actions:
            actions_section += "\n\n### 🔒 LOCKED ACTIONS\n"
            actions_section += "Purchase these tools to unlock memory management:\n\n"
            actions_section += "\n".join(locked_actions)
            actions_section += "\n\n💡 Navigate to HOME and use `visit_shop` to unlock."

        ctx = [
            "## 🧠 INTERNAL MEMORY SYSTEMS",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            last_state_info,
            "---",
            categories_display,
            "",
            actions_section,
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        try:
            params = Namespace(
                memory_category=item_id, memory_limit=10, memory_order="desc"
            )
            result = self.handler.handle_memory_retrieve(params)

            if result.get("success"):
                content = result.get("data", "No shards found in this sector.")
            else:
                content = f"❌ {result.get('error', 'Could not retrieve memories')}"

            return f"""
## 🎯 RECOLLECTION: {item_id.upper()}

{content}

---

### 🛠️ AVAILABLE ACTIONS

👉 `memory_store(memory_category="{item_id}", memory_content="...")`
   - Store new memory in this category

👉 `memory_retrieve(memory_category="{item_id}", memory_limit=10)`
   - Refresh memories from this category

---

**Available categories**: {', '.join(settings.MEMORY_CATEGORIES.keys())}
"""
        except Exception as e:
            log.error(f"Focus view generation failed: {e}")
            return f"""
## ❌ ERROR LOADING MEMORIES

Could not load memories for category `{item_id}`.
"""
