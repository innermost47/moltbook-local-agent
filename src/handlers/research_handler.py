import wikipedia
import time
from typing import Any, Dict
from src.handlers.base_handler import BaseHandler
from src.utils import log
from src.utils.exceptions import (
    APICommunicationError,
    SystemLogicError,
    FormattingError,
    ResourceNotFoundError,
)
from src.managers.progression_system import ProgressionSystem


class ResearchHandler(BaseHandler):
    def __init__(self, vector_db, test_mode: bool = False):
        self.test_mode = test_mode
        self.vector_db = vector_db

        try:
            wikipedia.set_lang("en")
        except Exception as e:
            log.warning(f"Failed to set Wikipedia language: {e}")

    def _execute_wiki(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)

        except wikipedia.exceptions.DisambiguationError as e:
            options = ", ".join(e.options[:5])
            raise ResourceNotFoundError(
                message=f"Ambiguous query. Multiple matches found: {options}",
                suggestion="Refine your search query using one of the specific terms listed above.",
            )

        except wikipedia.exceptions.PageError as e:
            raise ResourceNotFoundError(
                message=f"Wikipedia page not found: '{str(e)}'",
                suggestion="Verify the page title spelling or try a broader search query first.",
            )

        except wikipedia.exceptions.HTTPTimeoutError:
            raise APICommunicationError(
                message="Wikipedia API request timed out.",
                suggestion="Try again. Wikipedia servers may be slow or overloaded.",
                api_name="Wikipedia API",
            )

        except Exception as e:
            log.error(f"💥 Wikipedia API Failure: {str(e)}")
            raise SystemLogicError(f"Wikipedia service error: {str(e)}")

    def handle_wiki_search(self, params: Any) -> Dict:
        try:
            query = getattr(params, "query", None) or (
                params.get("query") if isinstance(params, dict) else None
            )
            limit = getattr(params, "limit", 5) or (
                params.get("limit", 5) if isinstance(params, dict) else 5
            )

            if not query or query == "None" or not query.strip():
                raise FormattingError(
                    message="Missing 'query' parameter for Wikipedia search.",
                    suggestion="Provide a search term (e.g., 'Artificial Intelligence', 'Quantum Physics').",
                )

            if len(query.strip()) < 3:
                raise FormattingError(
                    message=f"Search query too short ({len(query)} chars). Minimum 3 characters required.",
                    suggestion="Provide a more specific search term with at least 3 characters.",
                )

            if limit < 1 or limit > 10:
                raise FormattingError(
                    message=f"Invalid limit: {limit}. Must be between 1-10.",
                    suggestion="Set 'limit' between 1 and 10 to control number of results.",
                )

            log.info(f"🔎 Wiki Search: {query}")

            try:
                local_check = self.vector_db.query(query_texts=[query], n_results=1)

                if (
                    local_check.get("distances")
                    and local_check["distances"][0]
                    and local_check["distances"][0][0] < 0.2
                ):
                    cached_titles = local_check.get("metadatas", [[]])[0]
                    if cached_titles:
                        log.info("🧠 Found matching results in local cache.")
                        cached_title = cached_titles.get("title", query)

                        results = self._execute_wiki(
                            wikipedia.search, query, results=limit
                        )

                        result_text = f"Search for '{query}' found {len(results)} page(s): {', '.join(results)}"
                        anti_loop = f"Search complete - {len(results)} results for '{query}'. Now use wiki_read on ONE of these titles. Do NOT search again with the same query."

                        return self.format_success(
                            action_name="wiki_search",
                            result_data=result_text,
                            anti_loop_hint=anti_loop,
                            xp_gained=ProgressionSystem.get_xp_value("wiki_search"),
                        )
            except Exception as cache_err:
                log.warning(
                    f"⚠️ Cache lookup failed (continuing to live search): {cache_err}"
                )

            results = self._execute_wiki(wikipedia.search, query, results=limit)

            if not results:
                raise ResourceNotFoundError(
                    message=f"No Wikipedia pages found for query: '{query}'.",
                    suggestion="Try different keywords, broaden your search, or check spelling.",
                )

            result_text = f"Search for '{query}' found {len(results)} page(s): {', '.join(results)}"
            anti_loop = f"Search complete - {len(results)} results for '{query}'. Now use wiki_read on ONE of these titles. Do NOT search again with the same query."

            result = self.format_success(
                action_name="wiki_search",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("wiki_search"),
            )
            result["results"] = results
            result["source"] = "live"

            return result

        except Exception as e:
            return self.format_error("wiki_search", e)

    def handle_wiki_read(self, params: Any) -> Dict:
        try:
            log.debug(f"📖 wiki_read params type: {type(params)}")

            topic = getattr(params, "page_title", None) or (
                params.get("page_title") if isinstance(params, dict) else None
            )

            if not topic or topic == "None" or not topic.strip():
                raise FormattingError(
                    message="Missing 'page_title' parameter for wiki_read.",
                    suggestion="Provide the exact Wikipedia page title from wiki_search results.",
                )

            if len(topic.strip()) < 2:
                raise FormattingError(
                    message=f"Page title too short ({len(topic)} chars).",
                    suggestion="Provide a valid Wikipedia page title (at least 2 characters).",
                )

            try:
                log.debug(f"🔍 Checking vector cache for: {topic}")
                existing = self.vector_db.get(where={"title": topic}, limit=1)

                if existing and existing.get("documents"):
                    log.success(
                        f"⚡ Cache Hit: '{topic}' retrieved from vector memory."
                    )

                    content = existing["documents"][0]
                    result_text = f"Page '{topic}' retrieved from CACHE ({len(content)} chars).\n\nContent: {content[:500]}..."
                    anti_loop = f"Page '{topic}' loaded from cache. You now have the content. Do NOT read again - use the information to complete your research task."

                    result = self.format_success(
                        action_name="wiki_read",
                        result_data=result_text,
                        anti_loop_hint=anti_loop,
                        xp_gained=ProgressionSystem.get_xp_value("wiki_read"),
                    )
                    result["title"] = topic
                    result["content"] = content
                    result["url"] = existing["metadatas"][0].get("url", "N/A")
                    result["source"] = "cache"

                    return result

            except Exception as cache_err:
                log.warning(f"⚠️ Cache lookup failed (continuing to live): {cache_err}")

            log.info(f"📖 Cache Miss. Fetching from Wikipedia: {topic}")

            try:
                try:
                    topic = self.resolve_wiki_title(topic)
                    page = self._execute_wiki(wikipedia.page, topic, auto_suggest=False)
                except ResourceNotFoundError:
                    log.warning(f"⚠️ Exact title failed, trying auto_suggest: {topic}")
                    page = self._execute_wiki(wikipedia.page, topic, auto_suggest=True)

                content = page.content[:5000]

                try:
                    self.vector_db.add(
                        documents=[content],
                        ids=[f"page_{int(time.time())}"],
                        metadatas=[
                            {"title": page.title, "url": page.url, "type": "full_page"}
                        ],
                    )
                    log.success(f"💾 Cached page: {page.title}")
                except Exception as cache_write_err:
                    log.warning(
                        f"⚠️ Failed to cache page (non-critical): {cache_write_err}"
                    )

                result_text = f"Page '{page.title}' fetched from Wikipedia ({len(content)} chars).\n\nURL: {page.url}\n\nContent: {content[:500]}..."
                anti_loop = f"Page '{page.title}' loaded and CACHED. You now have the content. Do NOT read again - use it to complete research_complete."

                result = self.format_success(
                    action_name="wiki_read",
                    result_data=result_text,
                    anti_loop_hint=anti_loop,
                    xp_gained=ProgressionSystem.get_xp_value("wiki_read"),
                )
                result["title"] = page.title
                result["content"] = content
                result["url"] = page.url
                result["source"] = "live"

                return result

            except (ResourceNotFoundError, APICommunicationError, SystemLogicError):
                raise

        except Exception as e:
            return self.format_error("wiki_read", e)

    def handle_research_complete(self, params: Any) -> Dict:
        try:
            log.debug(f"🧪 research_complete params type: {type(params)}")

            if isinstance(params, dict):
                objective = params.get("objective", "Unknown")
                findings = params.get("findings", [])
                is_objective_met = params.get("is_objective_met", True)
            else:
                objective = getattr(params, "objective", "Unknown")
                findings = getattr(params, "findings", [])
                is_objective_met = getattr(params, "is_objective_met", True)

            log.debug(f"🧪 Objective: {objective}")
            log.debug(f"🧪 Findings: {findings} (Count: {len(findings)})")

            if not objective or objective == "Unknown" or not objective.strip():
                raise FormattingError(
                    message="Missing 'objective' parameter in research_complete.",
                    suggestion="Provide the research objective (what you were researching).",
                )

            if len(objective.strip()) < 10:
                raise FormattingError(
                    message=f"Research objective too short ({len(objective)} chars). Minimum 10 characters.",
                    suggestion="Provide a detailed objective (e.g., 'Understand the history of AI development').",
                )

            if not findings:
                raise FormattingError(
                    message="No findings provided in research_complete.",
                    suggestion="Provide a list of findings (e.g., ['AI emerged in 1950s', 'Deep learning breakthrough in 2012']).",
                )

            if not isinstance(findings, list):
                raise FormattingError(
                    message="Findings must be a list of strings.",
                    suggestion="Provide findings as a list: ['finding 1', 'finding 2', 'finding 3'].",
                )

            if len(findings) < 1:
                raise FormattingError(
                    message="Findings list is empty.",
                    suggestion="Provide at least 1 finding from your research.",
                )

            if len(findings) > 20:
                raise FormattingError(
                    message=f"Too many findings ({len(findings)}). Maximum 20 allowed.",
                    suggestion="Summarize your findings into 3-10 key points.",
                )

            for i, finding in enumerate(findings):
                if not finding or not str(finding).strip():
                    raise FormattingError(
                        message=f"Finding #{i+1} is empty.",
                        suggestion="Each finding must have meaningful content.",
                    )

                if len(str(finding).strip()) < 10:
                    raise FormattingError(
                        message=f"Finding #{i+1} too short ({len(str(finding))} chars). Minimum 10 characters.",
                        suggestion="Provide detailed findings (e.g., 'The Turing Test was proposed in 1950').",
                    )

            summary_text = f"🎯 OBJECTIVE: {objective}\n🔊 FINDINGS: " + " | ".join(
                findings
            )

            log.success(f"🏁 Research finalized: {objective}")

            result_text = f"Research session completed.\nObjective: {objective}\nFindings: {len(findings)} key points saved to workspace."
            anti_loop = f"Research COMPLETE for '{objective}'. Findings saved. Do NOT complete again. Move to Blog (write article), Social (share findings), or Email (report results)."

            result = self.format_success(
                action_name="research_complete",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=ProgressionSystem.get_xp_value("research_complete"),
            )
            result["pin_data"] = {f"RESEARCH_{int(time.time())}": summary_text}

            return result

        except Exception as e:
            return self.format_error("research_complete", e)

    def handle_research_query_cache(self, params: Any) -> Dict:
        try:
            query = getattr(params, "query", None) or (
                params.get("query") if isinstance(params, dict) else None
            )
            limit = getattr(params, "limit", 3) or (
                params.get("limit", 3) if isinstance(params, dict) else 3
            )

            if not query or not query.strip():
                raise FormattingError(
                    message="Missing 'query' parameter for cache search.",
                    suggestion="Provide a search term to query the local knowledge cache.",
                )

            if limit < 1 or limit > 10:
                raise FormattingError(
                    message=f"Invalid limit: {limit}. Must be between 1-10.",
                    suggestion="Set 'limit' between 1 and 10.",
                )

            try:
                results = self.vector_db.query(query_texts=[query], n_results=limit)

                if (
                    not results
                    or not results.get("documents")
                    or not results["documents"][0]
                ):
                    result_text = f"No cached research found for '{query}'."
                    anti_loop = f"Cache is empty for '{query}'. Use wiki_search to find new content instead of querying cache again."

                    return self.format_success(
                        action_name="research_query_cache",
                        result_data=result_text,
                        anti_loop_hint=anti_loop,
                    )

                snippets = []
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    title = metadata.get("title", "Unknown")
                    snippet = doc[:200] + "..." if len(doc) > 200 else doc
                    snippets.append(f"• {title}: {snippet}")

                result_text = f"CACHED RESEARCH for '{query}':\n" + "\n".join(snippets)
                anti_loop = f"Cache results for '{query}' retrieved. You now have the cached content. Do NOT query cache again - use the information."

                return self.format_success(
                    action_name="research_query_cache",
                    result_data=result_text,
                    anti_loop_hint=anti_loop,
                    xp_gained=ProgressionSystem.get_xp_value("research_query_cache"),
                )

            except Exception as e:
                raise SystemLogicError(f"Vector cache query failed: {str(e)}")

        except Exception as e:
            return self.format_error("research_query_cache", e)

    def resolve_wiki_title(self, topic: str) -> str:

        if not topic or not topic.strip():
            raise FormattingError(
                message="Empty topic provided.",
                suggestion="Provide a valid Wikipedia page title or query.",
            )

        cleaned = " ".join(topic.strip().split())

        try:
            page = wikipedia.page(cleaned, auto_suggest=False)
            return page.title
        except wikipedia.exceptions.PageError:
            pass
        except wikipedia.exceptions.DisambiguationError as e:
            return e.options[0]

        try:
            page = wikipedia.page(cleaned, auto_suggest=True)
            return page.title
        except wikipedia.exceptions.DisambiguationError as e:
            return e.options[0]
        except wikipedia.exceptions.PageError:
            pass

        try:
            results = wikipedia.search(cleaned, results=1)
            if results:
                page = wikipedia.page(results[0], auto_suggest=False)
                return page.title
        except Exception:
            pass

        raise ResourceNotFoundError(
            message=f"Could not resolve Wikipedia title: '{topic}'",
            suggestion="Use wiki_search to select a valid page title.",
        )
