from typing import Dict


class PlanContextManager:
    def __init__(self, plan_handler):
        self.handler = plan_handler

    def get_home_snippet(self) -> str:
        plan_data = self.handler.get_active_master_plan()
        if not plan_data:
            return "🗺️ **PLAN**: ⚠️ NO MASTER PLAN DEFINED. High priority: Set objective."

        obj = plan_data.get("objective", "Unknown")
        return f"🗺️ **PLAN**: Objective: {obj[:50]}..."

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:
        update_feedback = ""
        if result and result.get("success"):
            if result.get("action_type") in ["plan_update", "plan_initialize"]:
                update_feedback = (
                    f"### ✨ NEURAL ALIGNMENT SUCCESS\n> {result.get('data')}\n\n"
                )

        plan_context = self.handler.get_plan_context_for_prompt()

        ctx = [
            "## 🗺️ STRATEGIC PLANNING CENTER",
            f"{status_msg}" if status_msg else "",
            "---",
            update_feedback,
            "### 🎯 CURRENT MASTER PLAN",
            (
                plan_context
                if plan_context
                else "⚠️ *No active plan detected. System alignment required.*"
            ),
            "",
            "---",
            "### 🛠️ STRATEGIC CONTROLS",
            "* `plan_update` : Recalibrate the long-term trajectory.",
            "* `memory_store`: Archive current state to persistent logs.",
            "",
            "👉 **EXIT**: Use `refresh_home` to return to dashboard.",
        ]
        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        return self.get_list_view(status_msg=f"Focusing on Milestone aspect: {item_id}")
