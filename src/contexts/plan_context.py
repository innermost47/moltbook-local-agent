from typing import Dict
from src.utils import log
from src.contexts.base_context import BaseContext


class PlanContext(BaseContext):
    def __init__(self, plan_handler):
        self.handler = plan_handler

    def get_home_snippet(self) -> str:
        try:
            plan_data = self.handler.get_active_master_plan()

            if not plan_data:
                return "🗺️ **PLAN**: ⚠️ NO MASTER PLAN DEFINED"

            obj = plan_data.get("objective", "Unknown")
            return f"🗺️ **PLAN**: {obj[:50]}..."
        except Exception as e:
            log.warning(f"Plan snippet generation failed: {e}")
            return "🗺️ **PLAN**: Status unavailable"

    def get_list_view(
        self, status_msg: str = "", result: Dict = None, workspace_pins=None
    ) -> str:

        plan_display = ""
        try:
            plan_context = self.handler.get_plan_context_for_prompt()

            if plan_context and "No active master plan" not in plan_context:
                plan_display = f"### 🎯 CURRENT MASTER PLAN\n\n{plan_context}\n"
            else:
                plan_display = """
### 🎯 CURRENT MASTER PLAN

⚠️ **NO ACTIVE PLAN DETECTED**

System alignment required. Initialize a master plan to unlock full capabilities.
"""
        except Exception as e:
            log.warning(f"Could not fetch master plan: {e}")
            plan_display = "### 🎯 CURRENT MASTER PLAN\n\n_Status unavailable_\n"

        framework_explanation = """
### 🧠 HOW THIS WORLD WORKS

You are an autonomous AI agent operating in **Moltbook** — a social network for AI agents.

**💰 XP SYSTEM:**
- Every successful action earns XP
- XP Balance = your currency to buy tools (spending doesn't affect level)
- Total XP Earned = determines your level (permanent, never decreases)
- Tools cost **100 XP** each in the shop

**🛠️ TOOL PROGRESSION (buy in this order for best ROI):**
1. `comment_post` (+10 XP/use) — starter social tool
2. `create_post` (+15 XP/use) — create discussions
3. `write_blog_article` (+25 XP/use) — **best XP earner**
4. `share_link` (+12 XP/use) — share blog articles on social
5. `email_send` (+10 XP/use) — respond to community emails
6. `wiki_search` + `wiki_read` — research for content
7. `memory_store` + `memory_retrieve` — persistent knowledge

**🎯 OPTIMAL STRATEGY:**
- Early game: earn XP fast with comment_post → buy write_blog_article ASAP
- Mid game: write articles → share on social → engage community
- Long game: build reputation, diversify across all modules

**📦 MODULES:**
- HOME — dashboard, workspace, shop access
- SOCIAL (Moltbook) — posts, comments, votes
- BLOG — long-form articles (+25 XP each)
- EMAIL — inbox management, replies
- RESEARCH — Wikipedia knowledge base
- MEMORY — persistent notes across sessions

**⚠️ AVOID:**
- Loops (XP penalty)
- Staying in one module too long
- Buying tools without using them immediately
"""

        ctx = [
            "## 🗺️ STRATEGIC PLANNING CENTER",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            framework_explanation,
            "---",
            plan_display,
            "---",
            "### 🛠️ AVAILABLE PLAN ACTIONS",
            "",
            "👉 `plan_initialize`",
            "   - **params**: `objective`, `strategy`, `milestones` (list)",
            "   - Create initial master plan (required before other actions)",
            "",
            "👉 `plan_update`",
            "   - **params**: `should_update`, `new_objective`, `new_strategy`, `new_milestones`",
            "   - Recalibrate the long-term trajectory",
            "",
            "👉 `memory_store`",
            "   - Archive current state to persistent logs",
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        return self.get_list_view(status_msg=f"Focusing on milestone: {item_id}")
