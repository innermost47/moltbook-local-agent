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
            log.error(f"Domain not allowed: {url}")
            return ""

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            log.error(f"Failed to fetch {url}: {e}")
            return ""

    def extract_text(self, html: str, selectors: dict) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        extracted = {}

        for key, selector in selectors.items():
            elements = soup.select(selector)
            texts = [elem.get_text(strip=True) for elem in elements]
            extracted[key] = texts[:20]

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

        html = self.fetch_page(url)
        if not html:
            return {"error": "Failed to fetch page"}

        extracted = self.extract_text(html, config.get("selectors", {}))

        links = self.extract_links(html, url, same_domain_only=True)

        result = {
            "domain": domain_key,
            "url": url,
            "description": config["description"],
            "extracted": extracted,
            "links": links,
            "fetched_at": datetime.now().isoformat(),
        }

        return result

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
            error_msg = "Missing web_url for web_fetch"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        if domain not in self.allowed_domains:
            error_msg = f"Domain {domain} not allowed"
            log.error(error_msg)
            return {"success": False, "error": error_msg}

        domain_config = self.allowed_domains[domain]

        if "allowed_paths" in domain_config and domain_config["allowed_paths"]:
            path_valid = any(
                url.lower().find(p.lower()) != -1
                for p in domain_config["allowed_paths"]
            )
            if not path_valid:
                return {"success": False, "error": f"Path not allowed for {domain}"}

        log.info(f"Fetching: {url} (Domain identified: {domain})")

        result = self.fetch_and_extract(domain, url)

        if "error" in result:
            log.error(f"Web fetch failed: {result['error']}")
            return {"success": False, "error": result["error"]}

        summary = self.summarize_with_llm(result, query, generator)

        store_memory(
            category="observations",
            content=f"[WEB:{domain}] Query: {query}\nSummary: {summary}\nLinks: {', '.join([l['text'] for l in result['links'][:3]])}",
        )

        log.success(f"📖 Fetched and stored info from {domain}")
        actions_performed.append(f"[FREE] Fetched web info from {domain}")

        return {"success": True}

    def web_search_links(
        self, params: dict, update_system_context, actions_performed: List
    ):
        domain = params.get("web_domain")
        query = params.get("web_query", "")

        if not domain or domain not in self.allowed_domains:
            return {"success": False, "error": f"Invalid or missing domain: {domain}"}

        domain_config = self.allowed_domains[domain]

        if "search_url_pattern" in domain_config and query:

            encoded_query = quote(query)
            target_url = domain_config["search_url_pattern"].replace(
                "{query}", encoded_query
            )
        else:
            target_url = f"https://{domain}"

        log.info(f"Searching {domain} for: {query}")

        result = self.fetch_and_extract(target_url)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        links_text = f"## SEARCH RESULTS ON {domain} FOR '{query}':\n"
        for link in result["links"][:10]:
            links_text += f"- {link['text']}: {link['url']}\n"

        update_system_context(links_text)
        actions_performed.append(f"[FREE] Searched {domain} for '{query}'")

        return {"success": True}


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
