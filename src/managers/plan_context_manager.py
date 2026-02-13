from typing import Dict
from src.utils import log


class PlanContextManager:
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

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:
        action_feedback = ""

        if result:
            if result.get("success"):
                action_feedback = (
                    f"### ✅ LAST ACTION SUCCESS\n{result.get('data')}\n\n---\n"
                )
            else:
                if result.get("visual_feedback"):
                    action_feedback = f"### 🔴 LAST ACTION FAILED\n{result['visual_feedback']}\n\n---\n"
                else:
                    action_feedback = f"### ❌ LAST ACTION ERROR\n{result.get('error', 'Unknown error')}\n\n💡 {result.get('suggestion', 'Try again.')}\n\n---\n"

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

        ctx = [
            "## 🗺️ STRATEGIC PLANNING CENTER",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            action_feedback,
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
            "",
            "👉 `refresh_home`",
            "   - Return to dashboard",
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        return self.get_list_view(status_msg=f"Focusing on milestone: {item_id}")
