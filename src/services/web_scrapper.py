from typing import List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote
from src.utils import log
from src.settings import settings


class WebScraper:
    def __init__(self, test_mode=False):
        self.test_mode = test_mode
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
        if self.test_mode:
            log.info(f"🧪 [MOCK] Bypassing network fetch for: {url}")
            return """
            <html>
                <body>
                    <article>
                        <h1>Mocked Research Paper</h1>
                        <p>This is a simulated article about Zero Knowledge Proofs (ZKP) and decentralized systems.</p>
                        <a href="https://arxiv.org/abs/123.456">Deep Dive ZKP</a>
                        <a href="https://arxiv.org/abs/789.012">Trustless Computation</a>
                    </article>
                </body>
            </html>
            """
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

            texts = [
                elem.get_text(strip=True)
                for elem in elements
                if elem.get_text(strip=True)
            ]
            extracted[key] = texts[:20]

        total_content_found = sum(len(v) for k, v in extracted.items())

        if total_content_found == 0:
            log.warning(
                "No data found with specific selectors. Triggering global fallback..."
            )
            fallback_selectors = (
                "article, main, .content, .article, #content, #main, .post-content"
            )
            fallback_elements = soup.select(fallback_selectors)

            if not fallback_elements:
                fallback_elements = soup.find_all("p")

            fallback_text = [
                e.get_text(strip=True)
                for e in fallback_elements
                if e.get_text(strip=True)
            ]
            extracted["fallback_content"] = fallback_text[:30]

        extracted["_diagnostics"] = {
            "success": len(extracted.get("fallback_content", [])) > 0
            or len(missing_selectors) < len(selectors),
            "missing_keys": missing_selectors,
            "using_fallback": "fallback_content" in extracted,
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
        self, extracted_data: dict, query: str, llm_generator
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

    def web_fetch(self, params: dict, generator, store_memory, actions_performed: List):
        url = params.get("web_url", "").strip()

        if not url:
            url = params.get("web_domain", "").strip()

        if not url:
            return {
                "success": False,
                "error": "❌ Missing 'web_url'. Supply a valid URL.",
            }

        if not url.lower().startswith(("http://", "https://")):
            url = f"https://{url.lstrip(':/ ')}"

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower().replace("www.", "")

        if domain not in self.allowed_domains:
            allowed_list = ", ".join(self.allowed_domains.keys())
            return {
                "success": False,
                "error": f"❌ Domain '{domain}' is NOT in the whitelist. Authorized: {allowed_list}",
            }

        log.info(f"Fetching: {url} (Domain: {domain})")
        result = self.fetch_and_extract(domain, url)

        if "error" in result:
            return {"success": False, "error": f"❌ Fetch Failed: {result['error']}"}

        query = params.get("web_query", "")
        summary = self.summarize_with_llm(result, query, generator)

        store_memory(
            category="technical_intel",
            content=f"[WEB_INTEL:{domain}] Query: {query}\nSummary: {summary}\nSource: {url}",
        )

        log.success(f"Intel extracted from {domain} [^]")
        actions_performed.append(f"[FETCH] Web Fetch: {domain}")

        return {
            "success": True,
            "data": f"WEB CONTENT FETCHED FROM {url}:\n\n{summary}",
        }

    def web_scrap_for_links(self, params: dict, actions_performed: List):
        if self.test_mode:
            domain = params.get("web_domain", "test-source.com")
            query = params.get("web_query", "general")
            log.info(f"🧪 [MOCK] Bypassing real scrape for domain: {domain}")
            mock_links = [
                {
                    "text": f"Technical analysis of {query}",
                    "url": f"https://{domain}/article-1",
                },
                {
                    "text": f"Advanced protocols in {query}",
                    "url": f"https://{domain}/paper-v2",
                },
                {
                    "text": f"Community discussion on {query}",
                    "url": f"https://{domain}/thread-99",
                },
            ]
            links_text = f"SEARCH RESULTS ON {domain} FOR '{query}':\n"
            for link in mock_links:
                links_text += f"- {link['text']}: {link['url']}\n"

            actions_performed.append(f"[MOCK SEARCH] WEB SCRAPING FOR LINKS: {domain}")
            return {"success": True, "data": links_text}

        raw_input = params.get("web_domain", "").strip()
        if not raw_input:
            raw_input = params.get("web_url", "").strip()
        query = params.get("web_query", "")

        raw_input_low = raw_input.lower()
        if raw_input_low.startswith(("http://", "https://")):
            domain = urlparse(raw_input_low).netloc.lower().replace("www.", "")
        else:
            domain = raw_input_low.lstrip(":/ ").replace("www.", "")

        if not domain or domain not in self.allowed_domains and not self.test_mode:
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
            return {"success": True, "data": f"WEB SCRAPING FOR LINKS RESULT: {msg}"}

        links_text = f"SEARCH RESULTS ON {domain} FOR '{query}':\n"
        for link in result["links"][:10]:
            links_text += f"- {link['text']}: {link['url']}\n"

        log.success(f"Found {len(result['links'][:10])} links on {domain}")
        actions_performed.append(f"[SEARCH] WEB SCRAPING FOR LINKS: {domain}")

        result_to_return = {"success": True, "data": links_text}
        log.info(f"DEBUG - Returning from web_scrap_for_links: {result_to_return}")
        return result_to_return


def get_web_context_for_agent() -> str:
    context = "## 🌐 WEB ACCESS\n\n"
    context += "You can fetch information from these approved domains:\n\n"

    for domain, config in settings.get_domains().items():
        context += f"- **{domain}**: {config['description']}\n"
    context += f"\n\n---  \n\n"
    return context
