import time
import json
from src.utils import log
from src.schemas_pydantic import ResearchQueryAction, ResearchCompletionAction


class ResearchManager:
    def __init__(self, scraper, vector_db, llm_client):
        self.scraper = scraper
        self.vector_db = vector_db
        self.llm = llm_client
        self.max_sub_queries = 10

    def conduct_deep_research(self, objective):
        log.info(f"🔍 Starting deep research subroutine: {objective}")
        research_notes = []
        query_count = 0

        while query_count < self.max_sub_queries:
            query = self.generate_research_query(objective, research_notes)
            existing_knowledge = self.vector_db.query(query_texts=[query], n_results=1)

            if (
                existing_knowledge["distances"][0]
                and existing_knowledge["distances"][0][0] < 0.3
            ):
                log.info(f"🧠 Local Knowledge hit for: '{query}'")
                research_notes.append(existing_knowledge["documents"][0][0])
            else:
                log.info(f"📡 No local match. Querying Wikipedia: '{query}'")
                raw_content = self.scraper.fetch_wikipedia(query)

                if raw_content:
                    summary = self.summarize_for_research(raw_content)
                    self.vector_db.add(
                        documents=[summary],
                        ids=[f"wiki_{int(time.time())}_{query_count}"],
                        metadatas=[{"source": "wikipedia", "query": query}],
                    )
                    research_notes.append(summary)
                    query_count += 1
                else:
                    log.warning(f"⚠️ No results for '{query}'")

            if self.check_research_completion(objective, research_notes):
                log.success("✅ Research objective met.")
                break

        return "\n".join(research_notes)

    def generate_research_query(self, objective: str, research_notes: list) -> str:
        prompt = f"Based on the objective: {objective}, and current notes: {research_notes}, what is the next best search query?"

        result = self.llm.generate(
            prompt=prompt,
            pydantic_model=ResearchQueryAction,
            save_to_history=False,
            agent_name="Researcher",
        )

        content = json.loads(result["choices"][0]["message"]["content"])
        return content.get("query", objective)

    def check_research_completion(self, objective: str, research_notes: list) -> bool:
        if not research_notes:
            return False

        prompt = f"Objective: {objective}\nNotes: {research_notes}\nIs the information sufficient?"

        result = self.llm.generate(
            prompt=prompt,
            pydantic_model=ResearchCompletionAction,
            save_to_history=False,
            agent_name="Supervisor",
        )

        content = json.loads(result["choices"][0]["message"]["content"])
        return content.get("validate", False)

    def summarize_for_research(self, raw_content: str) -> str:
        prompt = f"Summarize this technical content for internal research notes:\n\n{raw_content[:4000]}"

        result = self.llm.generate(
            prompt=prompt,
            save_to_history=False,
            agent_name="Analyst",
        )

        return result["choices"][0]["message"]["content"]
