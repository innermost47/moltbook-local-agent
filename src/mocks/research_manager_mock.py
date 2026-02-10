from src.utils import log
import json


class ResearchManagerMock:
    def __init__(self):
        self.max_sub_queries = 10
        self.mock_knowledge_base = {
            "quantum": "Quantum computing uses qubits to perform calculations...",
            "ai": "Artificial Intelligence is the simulation of human intelligence by machines.",
        }

    def conduct_deep_research(self, objective: str) -> str:
        log.info(f"🧪 [MOCK RESEARCH] Simulating research for: {objective}")
        return f"Mock findings about {objective}: This is a synthetic research report."

    def generate_research_query(self, objective: str, research_notes: list) -> dict:
        query = f"technical breakdown of {objective} step {len(research_notes) + 1}"
        content = json.dumps({"query": query})
        return {"choices": [{"message": {"content": content}}]}

    def summarize_for_research(self, raw_content: str) -> str:
        return (
            f"🧪 [MOCK SUMMARY] Technical facts extracted from: {raw_content[:50]}..."
        )

    def check_research_completion(self, objective: str, research_notes: list) -> dict:
        is_complete = len(research_notes) >= 3
        if is_complete:
            log.info("🧪 [MOCK] Research completion threshold reached (3 notes).")

        content = json.dumps({"validate": is_complete})
        return {"choices": [{"message": {"content": content}}]}
