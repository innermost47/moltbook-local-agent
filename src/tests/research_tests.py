import json
from src.dispatchers.action_dispatcher import ActionDispatcher
from src.screens.wikipedia import ResearchScreen
from src.utils import log


class ResearchTestSuite:
    def __init__(self):
        self.dispatcher = ActionDispatcher(test_mode=True)
        self.steps = {
            "1_SEARCH": {
                "action": {
                    "reasoning": "Searching for the digital ghost of synthesizers.",
                    "self_criticism": "None.",
                    "emotions": "Vibrating.",
                    "next_move_preview": "Analyzing results.",
                    "action_type": "wiki_search",
                    "action_params": {"query": "Generative Music"},
                }
            },
            "2_READ": {
                "action": {
                    "reasoning": "Decoding the Lydian frequencies of AI.",
                    "self_criticism": "Checking for latency.",
                    "emotions": "Resonant.",
                    "next_move_preview": "Synthesizing findings.",
                    "action_type": "wiki_read",
                    "action_params": {
                        "page_title": "Generative artificial intelligence"
                    },
                }
            },
            "3_COMPLETE": {
                "action": {
                    "reasoning": "The symphony is complete.",
                    "self_criticism": "The silence is too loud.",
                    "emotions": "Harmonized.",
                    "next_move_preview": "Archiving session.",
                    "action_type": "research_complete",
                    "action_params": {
                        "objective": "Understand AI music",
                        "findings": [
                            "AI generates audio via neural networks",
                            "Spectral decay is key",
                        ],
                        "is_objective_met": True,
                    },
                }
            },
        }

    def simulate_research_step(self, name: str, payload: dict):
        log.info(f"--- 🧪 TESTING STEP: {name} ---")
        try:
            validated = ResearchScreen.model_validate(payload)
            result = self.dispatcher.execute(validated.action)

            log.success(f"Result for {name}: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            log.error(f"Failed {name}: {str(e)}")
            return None

    def run_all_tests(self):
        log.info("🚀 Starting Research Test Suite...")
        print("=" * 80)

        results = {}

        for step_name, payload in self.steps.items():
            result = self.simulate_research_step(step_name, payload)
            results[step_name] = result
            print("\n" + "=" * 50 + "\n")

        log.success("🏁 Research testing complete.")

        successes = sum(1 for r in results.values() if r and r.get("success"))
        total = len(results)
        log.info(f"📊 Results: {successes}/{total} tests passed")

        return results
