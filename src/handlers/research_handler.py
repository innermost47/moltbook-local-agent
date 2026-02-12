import wikipedia
import time
from typing import Any, Dict
from src.utils import log
from src.utils.exceptions import APICommunicationError, SystemLogicError


class ResearchHandler:
    def __init__(self, vector_db, test_mode: bool = False):
        self.test_mode = test_mode
        self.vector_db = vector_db
        wikipedia.set_lang("en")

    def _execute_wiki(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except wikipedia.exceptions.DisambiguationError as e:
            options = ", ".join(e.options[:5])
            raise APICommunicationError(
                f"Ambiguous query. Multiple matches found: {options}"
            )
        except wikipedia.exceptions.PageError:
            raise APICommunicationError(
                "Resource not found: The Wikipedia page does not exist."
            )
        except Exception as e:
            log.error(f"💥 Research System Failure: {str(e)}")
            raise SystemLogicError(f"External service error: {str(e)}")

    def handle_wiki_search(self, params: Any) -> Dict:
        query = getattr(params, "query", None) or (
            params.get("query") if isinstance(params, dict) else None
        )
        limit = getattr(params, "limit", 5) or (
            params.get("limit", 5) if isinstance(params, dict) else 5
        )

        if not query or query == "None":
            return {
                "success": False,
                "error": "Missing parameter: 'query' is required and cannot be null.",
            }

        log.info(f"🔎 Wiki Search: {query}")

        local_check = self.vector_db.query(query_texts=[query], n_results=1)

        if (
            local_check["distances"]
            and local_check["distances"][0]
            and local_check["distances"][0][0] < 0.2
        ):
            log.info("🧠 Found matching results in local cache.")
            return {
                "success": True,
                "data": f"Search successful for '{query}'. Found: {', '.join(results)}",
                "results": results,
                "source": "live",
            }
        results = self._execute_wiki(wikipedia.search, query, results=limit)

        if not results:
            return {
                "success": False,
                "error": f"No results found for query: '{query}'.",
            }

        return {
            "success": True,
            "data": f"Search successful for '{query}'. Found: {', '.join(results)}",
            "results": results,
            "source": "live",
        }

    def handle_research_complete(self, params: Any) -> Dict:
        log.debug(f"🧪 RESEARCH_COMPLETE: Incoming params type: {type(params)}")
        log.debug(f"🧪 RESEARCH_COMPLETE: Raw content: {params}")

        if isinstance(params, dict):
            objective = params.get("objective", "Unknown")
            findings = params.get("findings", [])
        else:
            objective = getattr(params, "objective", "Unknown")
            findings = getattr(params, "findings", [])

        log.debug(f"🧪 RESEARCH_COMPLETE: Objective extracted: {objective}")
        log.debug(
            f"🧪 RESEARCH_COMPLETE: Findings extracted: {findings} (Count: {len(findings)})"
        )

        if not findings:
            log.error("❌ RESEARCH_COMPLETE: Findings list is empty or None!")
            return {
                "success": False,
                "error": "Completion failed: No findings provided.",
            }

        summary_text = f"🎯 OBJECTIVE: {objective}\n🔊 FINDINGS: " + " | ".join(
            findings
        )

        log.success(f"🏁 Research finalized: {objective}")

        return {
            "success": True,
            "data": "Research completed and results summarized.",
            "pin_data": {f"RESEARCH_{int(time.time())}": summary_text},
        }

    def handle_wiki_read(self, params: Any) -> Dict:
        log.debug(f"Input params type: {type(params)}")
        topic = getattr(params, "page_title", None) or (
            params.get("page_title") if isinstance(params, dict) else None
        )

        if not topic or topic == "None":
            return {
                "success": False,
                "error": "Parameter error: 'page_title' is required.",
            }

        try:
            log.debug(f"Checking vector cache for: {topic}")
            existing = self.vector_db.get(where={"title": topic}, limit=1)

            if existing and existing.get("documents"):
                log.success(f"⚡ Cache Hit: '{topic}' retrieved from vector memory.")
                return {
                    "success": True,
                    "data": f"Retrieved from local neural cache (ID: {existing['ids'][0]})",
                    "title": topic,
                    "content": existing["documents"][0],
                    "url": existing["metadatas"][0].get("url", "N/A"),
                    "source": "cache",
                }
        except Exception as cache_err:
            log.warning(f"Cache lookup failed (continuing to live): {cache_err}")

        log.info(f"📖 Cache Miss. Deep Reading from Web: {topic}")

        try:
            page = self._execute_wiki(wikipedia.page, topic, auto_suggest=False)
            content = page.content[:5000]

            self.vector_db.add(
                documents=[content],
                ids=[f"page_{int(time.time())}"],
                metadatas=[{"title": page.title, "url": page.url, "type": "full_page"}],
            )

            return {
                "success": True,
                "data": f"Extracted {len(content)} chars from live Wikipedia.",
                "title": page.title,
                "content": content,
                "url": page.url,
                "source": "live",
            }
        except Exception as e:
            log.error(f"Wiki Extraction Error: {str(e)}")
            return {"success": False, "error": f"Extraction failed: {str(e)}"}
