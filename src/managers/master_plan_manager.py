import re
import json
from src.utils import log
from src.schemas_pydantic import MasterPlan, UpdateMasterPlan


class MasterPlanManager:
    def ensure_master_plan(self, app_steps):
        current_plan = app_steps.planning_system.get_active_master_plan()

        if not current_plan:
            log.warning("No Master Plan found. Forcing initialization...")

            init_prompt = app_steps.prompt_manager.get_master_master_plan_init_prompt(
                agent_name=app_steps.agent_name
            )
            try:
                result = app_steps.generator.generate(
                    init_prompt,
                    pydantic_model=MasterPlan,
                    agent_name=app_steps.agent_name,
                )
                assistant_msg = result["choices"][0]["message"]["content"]
                assistant_msg = re.sub(r"```json\s*|```\s*", "", assistant_msg).strip()
                plan_data = json.loads(assistant_msg)

                app_steps.planning_system.create_or_update_master_plan(
                    objective=plan_data.get("objective"),
                    strategy=plan_data.get("strategy"),
                    milestones=plan_data.get("milestones", []),
                )

                app_steps.master_plan_success_prompt = "✅ MASTER PLAN INITIALIZED: Your supreme goal and strategy are now active.\n"

                log.success(f"Master Plan initialized: {plan_data.get('objective')}")
                return False
            except Exception as e:
                log.error(f"Failed to initialize Master Plan: {e}")
                return True
        else:
            app_steps.master_plan_success_prompt = ""
            return True

    def update_master_plan_if_needed(self, summary: dict, app_steps):
        current_plan = app_steps.planning_system.get_active_master_plan()

        plan_json = (
            json.dumps(current_plan, indent=2) if current_plan else "NO MASTER PLAN YET"
        )

        app_steps.current_prompt = (
            app_steps.prompt_manager.get_update_master_plan_prompt(
                agent_name=app_steps.agent_name, plan_json=plan_json, summary=summary
            )
        )

        try:
            result = app_steps.generator.generate(
                app_steps.current_prompt,
                pydantic_model=UpdateMasterPlan,
                agent_name=app_steps.agent_name,
            )
            content = result["choices"][0]["message"]["content"]
            content = re.sub(r"```json\s*|```\s*", "", content).strip()
            if isinstance(content, str):
                decision = json.loads(content)
            else:
                decision = content

            if decision.get("should_update"):
                new_objective = decision.get("new_objective")
                new_strategy = decision.get("new_strategy")

                if not new_objective or not new_strategy:
                    log.warning(
                        "Master plan update skipped: missing objective or strategy"
                    )
                    log.info(f"Reason: {decision.get('reasoning')}")
                    return

                log.info(f"Updating master plan: {decision.get('reasoning')}")

                app_steps.planning_system.create_or_update_master_plan(
                    objective=new_objective,
                    strategy=new_strategy,
                    milestones=decision.get("new_milestones", []),
                )
            else:
                log.info(f"Master plan unchanged: {decision.get('reasoning')}")

        except Exception as e:
            log.error(f"Failed to evaluate master plan update: {e}")
