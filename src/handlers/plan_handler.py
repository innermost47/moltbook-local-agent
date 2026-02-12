from typing import Dict, Any, Optional
from src.utils import log
from src.utils.exceptions import SystemLogicError


class PlanHandler:

    def __init__(self, memory_handler):
        self.memory = memory_handler
        self.category = "master_plan"

    def get_active_master_plan(self) -> Optional[Dict[str, Any]]:
        plan = self.memory.get_active_master_plan()

        if plan:
            log.debug(f"🎯 Active Plan retrieved: {plan['objective'][:30]}...")
            return plan

        return None

    def has_active_plan(self) -> bool:
        plan = self.get_active_master_plan()
        return plan is not None

    def create_or_update_master_plan(
        self,
        objective: str,
        strategy: str,
        milestones: list,
        reasoning: str = "Initial setup",
    ):
        try:
            success = self.memory.create_or_update_master_plan(
                objective=objective, strategy=strategy, milestones=milestones
            )

            if success:
                log.success(f"💾 Master Plan synchronized in dedicated sector.")
                return {"success": True, "data": "Plan persisted and active."}
            else:
                raise SystemLogicError(
                    "MemoryHandler failed to write to master_plan table."
                )

        except Exception as e:
            log.error(f"❌ Master Plan sync failure: {e}")
            raise SystemLogicError(f"Could not persist strategy: {e}")

    def handle_plan_initialize(self, params: Any) -> Dict:
        def get_val(key, default=None):
            if isinstance(params, dict):
                return params.get(key, default)
            return getattr(params, key, default)

        objective = get_val("objective")
        strategy = get_val("strategy")
        milestones = get_val("milestones", [])
        reasoning = get_val("reasoning", "Initial setup")

        if not objective or not strategy:
            raise AttributeError(f"Missing objective/strategy in plan. Got: {params}")

        self.create_or_update_master_plan(
            objective=objective,
            strategy=strategy,
            milestones=milestones,
            reasoning=reasoning,
        )
        return {
            "success": True,
            "data": "✅ Master Plan initialized. Neural alignment confirmed.",
            "navigate_to": "home",
        }

    def handle_plan_update(self, params: Any) -> Dict:

        def get_val(key, default=None):
            if isinstance(params, dict):
                return params.get(key, default)
            return getattr(params, key, default)

        should_update = get_val("should_update", False)
        reasoning = get_val("reasoning", "Periodic recalibration")

        if should_update:
            new_obj = get_val("new_objective")
            new_strat = get_val("new_strategy")
            new_miles = get_val("new_milestones")

            if not new_obj or not new_strat:
                return {"success": False, "error": "Update requested but data missing."}

            self.create_or_update_master_plan(
                objective=new_obj,
                strategy=new_strat,
                milestones=new_miles,
                reasoning=reasoning,
            )
            return {
                "success": True,
                "action_type": "plan_update",
                "data": f"🔄 Master Plan evolved: {reasoning}",
            }

        return {
            "success": True,
            "action_type": "plan_update",
            "data": "📡 Strategy remains in resonance. No changes applied.",
        }

    def get_plan_context_for_prompt(self) -> str:
        plan_data = self.get_active_master_plan()

        if not plan_data:
            return "## 🗺️ MASTER PLAN\n⚠️ [CRITICAL] No active master plan. System is locked."

        objective = plan_data.get("objective", "Unknown")
        strategy = plan_data.get("strategy", "Unknown")
        milestones = plan_data.get("milestones", [])
        reasoning = plan_data.get("reasoning", "Current established trajectory.")

        milestones_str = "\n".join([f"   {i+1}. {m}" for i, m in enumerate(milestones)])

        return (
            f"## 🗺️ CURRENT MASTER PLAN\n"
            f"🎯 **OBJECTIVE**: {objective}\n"
            f"🧠 **STRATEGY**: {strategy}\n"
            f"📝 **REASONING**: {reasoning}\n"
            f"📍 **MILESTONES**:\n{milestones_str}\n"
            f"---"
        )
