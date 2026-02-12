import json
import time
from src.dispatchers.action_dispatcher import ActionDispatcher
from src.screens.global_actions import GlobalAction
from pydantic import BaseModel
from src.utils import log


class GlobalScreenMock(BaseModel):
    action: GlobalAction


class GlobalTestSuite:
    def __init__(self):
        self.dispatcher = ActionDispatcher(test_mode=True)

        class MockSession:
            def __init__(self):
                self.current_domain = "home"
                self.actions_remaining = 10
                self.pending_action = None

        self.dispatcher.set_session_manager(MockSession())

        self.steps = {
            "1_PIN_DATA": {
                "action": {
                    "reasoning": "Anchoring this harmonic shard for later use.",
                    "self_criticism": "None.",
                    "emotions": "Focused.",
                    "next_move_preview": "Proceeding with composition.",
                    "action_type": "pin_to_workspace",
                    "action_params": {
                        "label": "synth_fact_01",
                        "content": "Granular synthesis relies on small grains of sound (1-50ms).",
                    },
                }
            },
            "2_UNPIN_DATA": {
                "action": {
                    "reasoning": "Clearing the frequency space.",
                    "self_criticism": "Data is no longer needed.",
                    "emotions": "Analytical.",
                    "next_move_preview": "Checking remaining space.",
                    "action_type": "unpin_from_workspace",
                    "action_params": {"label": "synth_fact_01"},
                }
            },
            "3_NAVIGATE": {
                "action": {
                    "reasoning": "Switching to Social node.",
                    "self_criticism": "None.",
                    "emotions": "Ready.",
                    "next_move_preview": "Rendering Moltbook...",
                    "action_type": "navigate_to_mode",
                    "action_params": {
                        "chosen_mode": "SOCIAL",
                        "expected_actions_count": 10,
                    },
                }
            },
            "4_REFRESH_HOME": {
                "action": {
                    "reasoning": "Returning to core command center.",
                    "self_criticism": "None.",
                    "emotions": "Neutral.",
                    "next_move_preview": "Awaiting new signals.",
                    "action_type": "refresh_home",
                    "action_params": {},
                }
            },
        }

    def simulate_step(self, name: str, payload: dict):
        log.info(f"--- 🧪 TESTING GLOBAL ACTION: {name} ---")
        try:
            validated = GlobalScreenMock.model_validate(payload)

            result = self.dispatcher.execute(validated.action)

            if result.get("success"):
                log.success(f"✅ Success for {name}: {json.dumps(result, indent=2)}")
            else:
                log.error(f"❌ Logical Failure for {name}: {result.get('error')}")

            return result
        except Exception as e:
            log.error(f"💥 Validation/System Crash for {name}: {str(e)}")
            return None

    def run_all_tests(self):
        log.info("🚀 Starting Global Action Test Suite...")
        for step_name, payload in self.steps.items():
            self.simulate_step(step_name, payload)
            print("\n" + "━" * 50 + "\n")
