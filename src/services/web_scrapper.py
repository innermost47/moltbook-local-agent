from typing import List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote
from src.utils import log
from src.settings import settings
from src.generator import Generator


class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "MoltbookAgent/1.0 (Educational AI Agent)"}
        )
        self.allowed_domains = settings.get_domains()

    def is_allowed(self, url: str) -> bool:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        domain = domain.replace("www.", "")

        return domain in self.allowed_domains

    def fetch_page(self, url: str) -> str:
        if not self.is_allowed(url):
            error_msg = f"Security Violation: Domain not allowed for URL: {url}"
            log.error(error_msg)
            raise PermissionError(error_msg)

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            return response.text

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_msg = f"HTTP Error {status_code}: {e.response.reason} for URL: {url}"
            log.error(error_msg)
            raise Exception(error_msg)

        except requests.exceptions.Timeout:
            error_msg = f"Timeout Error: The server at {url} took too long to respond."
            log.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Network Error: {str(e)}"
            log.error(error_msg)
            raise Exception(error_msg)

    def extract_text(self, html: str, selectors: dict) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        extracted = {}
        missing_selectors = []

        for key, selector in selectors.items():
            elements = soup.select(selector)
            if not elements:
                missing_selectors.append(key)
                extracted[key] = []
                continue

            texts = [elem.get_text(strip=True) for elem in elements]
            extracted[key] = texts[:20]

        extracted["_diagnostics"] = {
            "success": len(missing_selectors) < len(selectors),
            "missing_keys": missing_selectors,
            "total_found": sum(
                len(v) for k, v in extracted.items() if k != "_diagnostics"
            ),
        }

        return extracted

    def extract_links(
        self, html: str, base_url: str, same_domain_only: bool = True
    ) -> list:

        soup = BeautifulSoup(html, "html.parser")
        links = []

        base_domain = urlparse(base_url).netloc

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)

            if same_domain_only:
                if urlparse(full_url).netloc == base_domain:
                    links.append(
                        {"url": full_url, "text": a_tag.get_text(strip=True)[:100]}
                    )
            else:
                if self.is_allowed(full_url):
                    links.append(
                        {"url": full_url, "text": a_tag.get_text(strip=True)[:100]}
                    )

        return links[:10]

    def fetch_and_extract(self, domain_key: str, url: str = None) -> dict:

        if domain_key not in self.allowed_domains:
            return {"error": f"Domain {domain_key} not allowed"}

        config = self.allowed_domains[domain_key]

        if not url:
            url = f"https://{domain_key}"

        log.info(f"Fetching: {url}")

        try:
            html = self.fetch_page(url)
            config = self.allowed_domains[domain_key]

            extracted_data = self.extract_text(html, config.get("selectors", {}))
            diagnostics = extracted_data.pop("_diagnostics")

            links = self.extract_links(html, url, same_domain_only=True)
            if diagnostics["total_found"] == 0:
                return {
                    "error": (
                        f"Empty Content: Page fetched successfully (200 OK), but no data was "
                        f"extracted using selectors for '{domain_key}'. The site structure might have changed."
                    )
                }

            return {
                "domain": domain_key,
                "url": url,
                "extracted": extracted_data,
                "links": links,
                "partial_failure": len(diagnostics["missing_keys"]) > 0,
                "missing_keys": diagnostics["missing_keys"],
            }

        except Exception as e:
            return {"error": str(e)}

    def summarize_with_llm(
        self, extracted_data: dict, query: str, llm_generator: Generator
    ) -> str:

        content_text = ""
        for key, items in extracted_data.get("extracted", {}).items():
            content_text += f"\n{key.upper()}:\n" + "\n".join(items[:10])

        summary_prompt = f"""
Summarize the following web content in 3-5 sentences, focusing on: {query}

Content from {extracted_data['domain']}:
{content_text[:2000]}

Provide a concise summary (max 300 words) highlighting the most relevant information.
"""

        try:
            summary = llm_generator.generate_simple(summary_prompt, max_tokens=300)
            return summary
        except Exception as e:
            log.error(f"Failed to summarize: {e}")
            return content_text[:500] + "..."

    def web_fetch(
        self, params: dict, generator: Generator, store_memory, actions_performed: List
    ):
        url = params.get("web_url")
        query = params.get("web_query", "")

        if not url:
            return {
                "success": False,
                "error": "❌ Missing 'web_url'. Supply a valid URL from the allowed domains.",
            }

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower().replace("www.", "")

        if domain not in self.allowed_domains:
            allowed_list = ", ".join(self.allowed_domains.keys())
            return {
                "success": False,
                "error": f"❌ Domain '{domain}' is NOT in the whitelist.\nAuthorized domains: {allowed_list}",
            }

        domain_config = self.allowed_domains[domain]
        if "allowed_paths" in domain_config and domain_config["allowed_paths"]:
            path_valid = any(
                p.lower() in url.lower() for p in domain_config["allowed_paths"]
            )
            if not path_valid:
                paths = ", ".join(domain_config["allowed_paths"])
                return {
                    "success": False,
                    "error": f"❌ Path access denied for {domain}. Authorized paths: {paths}",
                }

        log.info(f"Fetching: {url} (Domain: {domain})")

        result = self.fetch_and_extract(domain, url)

        if "error" in result:
            return {"success": False, "error": f"❌ Fetch Failed: {result['error']}"}

        summary = self.summarize_with_llm(result, query, generator)

        store_memory(
            category="technical_intel",
            content=f"[WEB_INTEL:{domain}] Query: {query}\nSummary: {summary}\nSource: {url}",
        )

        log.success(f"Intel extracted from {domain} [^]")
        actions_performed.append(f"[FREE] Web Fetch: {domain}")

        return {
            "success": True,
            "data": f"WEB CONTENT FETCHED FROM {url}:\n\n{summary}",
        }

    def web_search_links(self, params: dict, actions_performed: List):
        domain = params.get("web_domain", "").lower().replace("www.", "")
        query = params.get("web_query", "")

        if domain not in self.allowed_domains:
            allowed_list = ", ".join(self.allowed_domains.keys())
            return {
                "success": False,
                "error": f"❌ Invalid domain '{domain}'. Authorized sources: {allowed_list}",
            }

        domain_config = self.allowed_domains[domain]

        if "search_url_pattern" in domain_config and query:
            target_url = domain_config["search_url_pattern"].replace(
                "{query}", quote(query)
            )
        else:
            target_url = f"https://{domain}"

        log.info(f"Searching {domain} for: {query}")

        result = self.fetch_and_extract(domain, target_url)

        if "error" in result:
            return {"success": False, "error": f"❌ Search Failed: {result['error']}"}

        if not result.get("links"):
            msg = f"No relevant links found on {domain} for '{query}'."
            log.info(msg)
            return {"success": True, "data": f"WEB SEARCH RESULT: {msg}"}

        links_text = f"SEARCH RESULTS ON {domain} FOR '{query}':\n"
        for link in result["links"][:10]:
            links_text += f"- {link['text']}: {link['url']}\n"

        log.success(f"Found {len(result['links'][:10])} links on {domain}")
        actions_performed.append(f"[FREE] Web Search: {domain}")

        return {"success": True, "data": links_text}


def get_web_context_for_agent() -> str:
    context = "## WEB ACCESS (FREE ACTIONS)\n\n"
    context += "You can fetch information from these approved domains:\n\n"

    for domain, config in settings.get_domains().items():
        context += f"- **{domain}**: {config['description']}\n"

    context += "\n**Web Actions:**\n"
    context += "- web_fetch: Fetch and extract content from an allowed domain\n"
    context += "- web_search_links: Get links from a domain page\n"
    context += "**Important:** Web results are automatically summarized to save context space.\n"

    return context
