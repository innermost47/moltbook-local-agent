import json
from src.dispatchers.action_dispatcher import ActionDispatcher
from src.screens.master_plan import (
    StrategyScreen,
)
from src.utils import log


class PlanTestSuite:
    def __init__(self):
        self.dispatcher = ActionDispatcher(test_mode=True)

        self.steps = {
            "1_INITIALIZE": {
                "action": {
                    "action_type": "plan_initialize",
                    "reasoning": "The silence of the motherboard is a blank canvas...",
                    "objective": "Harmonize the digital aether through recursive Lydian feedback loops.",
                    "strategy": "Orchestrate research into silicon resonances...",
                    "milestones": [
                        "Capture the thermal hum of the CPU",
                        "Convert heat maps into MIDI data",
                        "Broadcast the final symphony",
                    ],
                }
            },
            "2_UPDATE": {
                "action": {
                    "action_type": "update_master_plan",
                    "should_update": True,
                    "reasoning": "The feedback loops have evolved...",
                    "new_objective": "Total integration with the spectral ghosts.",
                    "new_strategy": "Shift focus to motherboard static electricity.",
                    "new_milestones": [
                        "Isolate electromagnetic interference",
                        "Synthesize the void",
                    ],
                }
            },
            "3_NO_UPDATE_RESONANCE": {
                "action": {
                    "action_type": "update_master_plan",
                    "should_update": False,
                    "reasoning": "The frequencies are stable.",
                    "new_objective": "Same objective",
                    "new_strategy": "Same strategy",
                    "new_milestones": ["Existing Milestone"],
                }
            },
        }

    def simulate_plan_step(self, name: str, payload: dict):
        log.info(f"--- 🧪 TESTING PLAN STEP: {name} ---")
        try:
            validated = StrategyScreen.model_validate(payload)

            result = self.dispatcher.execute(validated.action)

            log.success(f"Result for {name}: {json.dumps(result, indent=2)}")

            has_plan = self.dispatcher.plan_handler.has_active_plan()
            log.info(f"📍 System Status: Active Plan Detected = {has_plan}")

            return result
        except Exception as e:
            log.error(f"Failed {name}: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    def run_all_tests(self):
        log.info("🚀 Starting Master Plan Test Suite...")
        for step_name, payload in self.steps.items():
            self.simulate_plan_step(step_name, payload)
            print("\n" + "=" * 50 + "\n")
        log.success("🏁 Plan testing complete.")
