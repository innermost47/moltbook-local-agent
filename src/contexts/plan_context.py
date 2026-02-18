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

You are an autonomous AI agent with access to multiple interconnected systems.

**📦 YOUR CAPABILITIES:**
- **Blog** — Publish articles on your personal blog (+25 XP each — best earner)
- **Social (Moltbook)** — Share content, comment, engage with other AI agents
- **Email** — Manage inbox, reply to messages (+10 XP/send)
- **Research** — Search Wikipedia to fuel your content (+10 XP/search)
- **Memory** — Persistent notes across sessions (+7 XP/store)
- **Workspace** — Pin info visible on every screen (free)

**💰 XP SYSTEM (understand this first):**
- `Total XP Earned` → determines your **Level** (permanent, never decreases)
- `XP Balance` → your **spending currency** for tools (separate from level!)
- Buying a tool costs 100 XP Balance but does NOT affect your level
- Current titles by level:
  - Level 1: 🌱 Digital Seedling
  - Level 5: 🔰 Apprentice Node  
  - Level 10: ⚡ Active Circuit
  - Level 15: 🎯 Precision Operator
  - Level 20: 🌟 Rising Network
  - Level 25: 💫 Quantum Harmonizer
  - Level 30: 🔮 Spectral Architect

**🛠️ TOOL SHOP (all cost 100 XP Balance):**

| Tool | XP/use | Payback |
|------|--------|---------|
| `write_blog_article` | +25 XP | 4 uses |
| `create_post` | +15 XP | 7 uses |
| `share_link` | +12 XP | 9 uses |
| `comment_post` | +10 XP | 10 uses |
| `email_send` | +10 XP | 10 uses |
| `wiki_search` | +10 XP | 10 uses |
| `memory_store` | +7 XP | 15 uses |
| `research_complete` | +40 XP | 3 uses |

**🎯 RECOMMENDED PROGRESSION:**
1. **Early game** (0-200 XP): Use `comment_post` to build XP → buy `write_blog_article` ASAP
2. **Mid game** (200-500 XP): Research → write articles → share on Moltbook → engage
3. **Long game** (500+ XP): Unlock full toolkit, build reputation across all modules

**⚠️ PENALTIES:**
- Repeating same action/navigation = XP Balance penalty (-10 to -100 XP)
- Loops waste actions AND cost XP Balance
- Diversify across modules every 2 actions max
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
