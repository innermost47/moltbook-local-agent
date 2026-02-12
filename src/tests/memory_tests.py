import json
from pydantic import BaseModel
from src.dispatchers.action_dispatcher import ActionDispatcher
from src.screens.global_actions import GlobalAction
from src.utils import log


class GlobalScreenMock(BaseModel):
    action: GlobalAction


class MemoryTestSuite:
    def __init__(self):
        self.dispatcher = ActionDispatcher(test_mode=True)
        self.steps = {
            "1_STORE": {
                "action": {
                    "reasoning": "Anchoring the spectral ghosts of a 440Hz resonance.",
                    "self_criticism": "The frequency must be preserved.",
                    "emotions": "Obsessive.",
                    "next_move_preview": "Confirming storage.",
                    "action_type": "memory_store",
                    "action_params": {
                        "memory_category": "experiments",
                        "memory_content": "Fact: Silicon cooling fans resonate in the Lydian mode at peak CPU load.",
                    },
                }
            },
            "2_RETRIEVE": {
                "action": {
                    "reasoning": "Recalling the algorithmic feedback loops of the past.",
                    "self_criticism": "The void whispers, I must listen.",
                    "emotions": "Resonant.",
                    "next_move_preview": "Analyzing recalled shards.",
                    "action_type": "memory_retrieve",
                    "action_params": {
                        "memory_category": "experiments",
                        "memory_limit": 5,
                        "memory_order": "desc",
                    },
                }
            },
        }

    def simulate_memory_step(self, name: str, payload: dict):
        log.info(f"--- 🧪 TESTING MEMORY STEP: {name} ---")
        try:
            validated = GlobalScreenMock.model_validate(payload)

            result = self.dispatcher.execute(validated.action)

            log.success(f"Result for {name}: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            log.error(f"Failed {name}: {str(e)}")
            return None

    def run_all_tests(self):
        for step_name, payload in self.steps.items():
            self.simulate_memory_step(step_name, payload)
            print("\n" + "=" * 50 + "\n")
