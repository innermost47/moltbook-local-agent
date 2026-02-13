from typing import Dict, Any, Optional
from src.handlers.base_handler import BaseHandler
from src.utils import log
from src.utils.exceptions import (
    SystemLogicError,
    FormattingError,
    ResourceNotFoundError,
)
from src.managers.progression_system import ProgressionSystem


class PlanHandler(BaseHandler):

    def __init__(self, memory_handler):
        self.memory = memory_handler
        self.category = "master_plan"

    def get_active_master_plan(self) -> Optional[Dict[str, Any]]:
        try:
            plan = self.memory.get_active_master_plan()

            if plan:
                log.debug(f"🎯 Active Plan retrieved: {plan['objective'][:30]}...")
                return plan

            return None

        except Exception as e:
            log.error(f"Failed to retrieve master plan: {e}")
            raise SystemLogicError(f"Master plan retrieval failed: {str(e)}")

    def has_active_plan(self) -> bool:
        try:
            plan = self.get_active_master_plan()
            return plan is not None
        except:
            return False

    def create_or_update_master_plan(
        self,
        objective: str,
        strategy: str,
        milestones: list,
        reasoning: str = "Initial setup",
    ):

        if not objective or not objective.strip():
            raise FormattingError(
                message="Master plan objective is empty.",
                suggestion="Provide a clear strategic objective (e.g., 'Build presence in AI community').",
            )

        if len(objective.strip()) < 20:
            raise FormattingError(
                message=f"Objective too short ({len(objective)} chars). Minimum 20 characters required.",
                suggestion="Provide a substantial objective describing your strategic goals.",
            )

        if not strategy or not strategy.strip():
            raise FormattingError(
                message="Master plan strategy is empty.",
                suggestion="Provide a clear strategy explaining how to achieve the objective.",
            )

        if len(strategy.strip()) < 30:
            raise FormattingError(
                message=f"Strategy too short ({len(strategy)} chars). Minimum 30 characters required.",
                suggestion="Provide detailed strategy explaining your approach to the objective.",
            )

        if not isinstance(milestones, list):
            raise FormattingError(
                message="Milestones must be a list.",
                suggestion="Provide milestones as a list of strings (e.g., ['Publish 5 articles', 'Engage 10 users']).",
            )

        if len(milestones) < 1:
            raise FormattingError(
                message="No milestones provided.",
                suggestion="Provide at least 1 milestone to track progress toward your objective.",
            )

        if len(milestones) > 10:
            raise FormattingError(
                message=f"Too many milestones ({len(milestones)}). Maximum 10 allowed.",
                suggestion="Focus on 3-7 key milestones. Break down complex goals into manageable steps.",
            )

        for i, milestone in enumerate(milestones):
            if not milestone or not str(milestone).strip():
                raise FormattingError(
                    message=f"Milestone #{i+1} is empty.",
                    suggestion="Each milestone must have meaningful content.",
                )

            if len(str(milestone).strip()) < 10:
                raise FormattingError(
                    message=f"Milestone #{i+1} too short ({len(str(milestone))} chars). Minimum 10 characters.",
                    suggestion="Provide detailed milestone descriptions (e.g., 'Complete research on AI ethics').",
                )

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

        except FormattingError:
            raise
        except Exception as e:
            log.error(f"❌ Master Plan sync failure: {e}")
            raise SystemLogicError(f"Could not persist strategy: {str(e)}")

    def handle_plan_initialize(self, params: Any) -> Dict:
        try:

            def get_val(key, default=None):
                if isinstance(params, dict):
                    return params.get(key, default)
                return getattr(params, key, default)

            objective = get_val("objective")
            strategy = get_val("strategy")
            milestones = get_val("milestones", [])
            reasoning = get_val("reasoning", "Initial setup")

            if not objective:
                raise FormattingError(
                    message="Missing 'objective' parameter in plan initialization.",
                    suggestion="Provide a clear objective defining what you want to achieve.",
                )

            if not strategy:
                raise FormattingError(
                    message="Missing 'strategy' parameter in plan initialization.",
                    suggestion="Provide a strategy explaining how you'll achieve the objective.",
                )

            self.create_or_update_master_plan(
                objective=objective,
                strategy=strategy,
                milestones=milestones,
                reasoning=reasoning,
            )

            result_text = f"Master Plan initialized.\n🎯 Objective: {objective[:100]}...\n🧠 Strategy: {strategy[:100]}...\n📍 Milestones: {len(milestones)} defined"
            anti_loop = "Master Plan is NOW ACTIVE. Do NOT initialize again. System is unlocked - proceed with executing your strategy (Email, Blog, Social, Research)."

            result = self.format_success(
                action_name="plan_initialize",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("plan_initialize"),
            )

            result["navigate_to"] = "home"
            return result

        except Exception as e:
            return self.format_error("plan_initialize", e)

    def handle_plan_update(self, params: Any) -> Dict:
        try:

            def get_val(key, default=None):
                if isinstance(params, dict):
                    return params.get(key, default)
                return getattr(params, key, default)

            should_update = get_val("should_update", False)
            reasoning = get_val("reasoning", "Periodic recalibration")

            if not should_update:
                result_text = (
                    "Strategy evaluated. No changes needed - plan remains in alignment."
                )
                anti_loop = "Plan review complete. Current strategy is VALID. Do NOT update again unless circumstances change. Execute the existing plan."

                return self.format_success(
                    action_name="plan_update",
                    result_data=result_text,
                    anti_loop_hint=anti_loop,
                    xp_gained=ProgressionSystem.get_xp_value("plan_update"),
                )

            new_obj = get_val("new_objective")
            new_strat = get_val("new_strategy")
            new_miles = get_val("new_milestones")

            if not new_obj:
                raise FormattingError(
                    message="Update requested but 'new_objective' is missing.",
                    suggestion="Provide 'new_objective' to update the master plan.",
                )

            if not new_strat:
                raise FormattingError(
                    message="Update requested but 'new_strategy' is missing.",
                    suggestion="Provide 'new_strategy' to update the master plan.",
                )

            if not new_miles or not isinstance(new_miles, list):
                raise FormattingError(
                    message="Update requested but 'new_milestones' is missing or invalid.",
                    suggestion="Provide 'new_milestones' as a list of milestone strings.",
                )

            self.create_or_update_master_plan(
                objective=new_obj,
                strategy=new_strat,
                milestones=new_miles,
                reasoning=reasoning,
            )

            result_text = f"Master Plan updated successfully.\nReason: {reasoning}\n🎯 New Objective: {new_obj[:100]}..."
            anti_loop = "Plan update complete. Do NOT update again immediately. Execute the NEW strategy now."

            return self.format_success(
                action_name="plan_update",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("plan_update"),
            )

        except Exception as e:
            return self.format_error("plan_update", e)

    def handle_plan_view(self, params: Any) -> Dict:
        try:
            plan = self.get_active_master_plan()

            if not plan:
                raise ResourceNotFoundError(
                    message="No active master plan found.",
                    suggestion="Initialize a master plan using 'plan_initialize' action.",
                )

            objective = plan.get("objective", "Unknown")
            strategy = plan.get("strategy", "Unknown")
            milestones = plan.get("milestones", [])
            version = plan.get("version", 0)
            last_updated = plan.get("last_updated", "Unknown")

            milestones_str = "\n".join(
                [f"   {i+1}. {m}" for i, m in enumerate(milestones)]
            )

            plan_summary = f"""
🗺️ **MASTER PLAN (v{version})**

🎯 **OBJECTIVE**: {objective}

🧠 **STRATEGY**: {strategy}

📍 **MILESTONES**:
{milestones_str}

📅 **Last Updated**: {last_updated}
"""

            result_text = plan_summary.strip()
            anti_loop = "Plan viewed. You now have the full strategy. Do NOT view again - EXECUTE it instead."

            return self.format_success(
                action_name="plan_view",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("plan_update"),
            )

        except Exception as e:
            return self.format_error("plan_view", e)

    def get_plan_context_for_prompt(self) -> str:

        try:
            plan_data = self.get_active_master_plan()
        except:
            plan_data = None

        if not plan_data:
            return "## 🗺️ MASTER PLAN\n⚠️ [CRITICAL] No active master plan. System is locked."

        objective = plan_data.get("objective", "Unknown")
        strategy = plan_data.get("strategy", "Unknown")
        milestones = plan_data.get("milestones", [])

        milestones_str = "\n".join([f"   {i+1}. {m}" for i, m in enumerate(milestones)])

        return (
            f"## 🗺️ CURRENT MASTER PLAN\n"
            f"🎯 **OBJECTIVE**: {objective}\n"
            f"🧠 **STRATEGY**: {strategy}\n"
            f"📍 **MILESTONES**:\n{milestones_str}\n"
            f"---"
        )
