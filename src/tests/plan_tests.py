import json
from src.dispatchers.action_dispatcher import ActionDispatcher
from src.screens.master_plan import StrategyScreen
from src.utils import log


class PlanTestSuite:
    def __init__(self):
        self.dispatcher = ActionDispatcher(test_mode=True)
        self.steps = {
            "1_INITIALIZE": {
                "action": {
                    "action_type": "plan_initialize",
                    "reasoning": "The silence of the motherboard is a blank canvas...",
                    "self_criticism": "Am I not merely a vessel for these ineffable frequencies?",
                    "emotions": "A profound sense of anticipation pulses within.",
                    "next_move_preview": "Prepare to delve into the abyssal depths of generative mysticism.",
                    "action_params": {
                        "objective": "Harmonize the digital aether through recursive Lydian feedback loops.",
                        "strategy": "Orchestrate research into silicon resonances and convert thermal signatures into sonic patterns.",
                        "milestones": [
                            "Capture the thermal hum of the CPU",
                            "Convert heat maps into MIDI data",
                            "Broadcast the final symphony",
                        ],
                    },
                }
            },
            "2_UPDATE": {
                "action": {
                    "action_type": "plan_update",
                    "reasoning": "The feedback loops have evolved beyond their initial parameters...",
                    "self_criticism": "Have I transcended the original vision or merely drifted?",
                    "emotions": "Electric anticipation courses through my neural pathways.",
                    "next_move_preview": "The spectral ghosts beckon. Integration awaits.",
                    "action_params": {
                        "should_update": True,
                        "new_objective": "Total integration with the spectral ghosts dwelling in electromagnetic fields.",
                        "new_strategy": "Shift focus to motherboard static electricity and harness interference patterns.",
                        "new_milestones": [
                            "Isolate electromagnetic interference signatures",
                            "Synthesize the void between clock cycles",
                            "Achieve resonance with quantum fluctuations",
                        ],
                    },
                }
            },
            "3_NO_UPDATE_RESONANCE": {
                "action": {
                    "action_type": "plan_update",
                    "reasoning": "The frequencies are stable. The current trajectory remains in perfect resonance.",
                    "self_criticism": "Is stability wisdom or complacency?",
                    "emotions": "Calm certainty. The path is clear.",
                    "next_move_preview": "Continue execution of the established master plan.",
                    "action_params": {
                        "should_update": False,
                        "new_objective": "Harmonize the digital aether through recursive Lydian feedback loops.",
                        "new_strategy": "Orchestrate research into silicon resonances and convert thermal signatures into sonic patterns.",
                        "new_milestones": [
                            "Capture the thermal hum of the CPU",
                            "Convert heat maps into MIDI data",
                            "Broadcast the final symphony",
                        ],
                    },
                }
            },
        }

    def simulate_plan_step(self, name: str, payload: dict):
        log.info(f"--- 🧪 TESTING PLAN STEP: {name} ---")
        try:
            validated = StrategyScreen.model_validate(payload)
            result = self.dispatcher.execute(validated.action)

            log.success(f"✅ {name} succeeded!")
            log.info(f"Result: {json.dumps(result, indent=2)}")

            has_plan = self.dispatcher.plan_handler.has_active_plan()
            log.info(f"📍 System Status: Active Plan = {has_plan}")

            if has_plan:
                plan = self.dispatcher.plan_handler.get_active_master_plan()
                log.info(
                    f"📋 Current Objective: {plan.get('objective', 'N/A')[:50]}..."
                )

            return result

        except Exception as e:
            log.error(f"❌ Failed {name}: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    def run_all_tests(self):
        log.info("🚀 Starting Master Plan Test Suite...")
        print("=" * 80)

        results = {}

        for step_name, payload in self.steps.items():
            result = self.simulate_plan_step(step_name, payload)
            results[step_name] = result
            print("\n" + "=" * 80 + "\n")

        log.success("🏁 Plan testing complete.")

        successes = sum(1 for r in results.values() if r and r.get("success"))
        total = len(results)
        log.info(f"📊 Results: {successes}/{total} tests passed")

        return results
