from typing import Dict
from src.utils import log


class ResearchContextManager:
    def __init__(self, research_handler):
        self.handler = research_handler

    def get_home_snippet(self) -> str:
        return "🔍 **RESEARCH**: Wikipedia module active. Local vector cache enabled."

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:
        search_content = ""

        if result and "results" in result:
            titles = result["results"]
            search_content = "### 📑 AVAILABLE TITLES\n"
            for title in titles:
                search_content += f"* `{title}`\n"

            search_content += (
                "\n⚠️ **DIRECTIVE**: Select one of the titles above for `wiki_read`."
            )

        return f"""
## 🔍 RESEARCH CENTER
{f"✅ **STATUS**: {status_msg}" if status_msg else ""}
---
{search_content if search_content else "_No data currently active._"}
---
👉 **RESEARCH PROTOCOL**:
1. 🔍 `wiki_search` : Use ONCE to discover specific page titles.
2. 📖 `wiki_read` : Use to extract deep knowledge from a title found. **Mandatory step** before completing.
3. ✅ `research_complete` : Use to synthesize and SAVE your findings to long-term memory.

⚠️ **WARNING**: Avoid redundant searches. If you have titles, move to READ phase.
"""

    def get_focus_view(self, item_id: str) -> str:
        log.debug(f"🔍 UI FOCUS: Rendering for '{item_id}'")

        if not item_id or item_id == "None":
            log.warning("⚠️ UI FOCUS: item_id is missing or 'None'")
            return "❌ **ERROR**: No valid title provided to focus. Please select a title from the search results."

        Params = type(
            "Params", (), {"page_title": item_id, "topic": item_id, "sentences": 5}
        )

        try:
            result = self.handler.handle_wiki_read(Params())

            if not result.get("success"):
                return f"❌ **RESEARCH ERROR**: {result.get('error', 'Unknown error')}"

            content = result.get("content") or "No content available."
            source = result.get("source", "external")
            display_title = result.get("title", item_id)

            return f"""
# 🎯 RESEARCH FOCUS: {display_title.upper()}
**Source:** Wikipedia ({source})

{content[:2000]}... *(truncated for UI)*

---

### 📌 WORKSPACE PERSISTENCE
**Carry this information across modules by pinning it to your dashboard.**
👉 **ACTION**: `pin_to_workspace(label="UNIQUE_ID", content="TEXT_TO_SAVE")`
> 💡 **Why?** Content inside the workspace remains visible even after you navigate to other modes (Email, Blog, Social). Use this to avoid losing critical data.

---

### 🛠️ NEXT STEPS & WORKFLOWS
**Once you have extracted the necessary data, choose your next trajectory:**

- ✅ **FINALIZE**: `research_complete(objective="...", findings=["...", "..."])`  
  _Crucial: You MUST explicitly list your findings in the params to anchor them._
- ✍️ **CREATE CONTENT**: `Maps_to_mode(chosen_mode="BLOG")`  
  _Pin your data first, then switch to the Blog module to write an article._
- 📡 **SHARE UPDATES**: `Maps_to_mode(chosen_mode="SOCIAL")`  
  _Pin key highlights to draft a Moltbook post in the Social module._
- 📩 **RESPOND**: `Maps_to_mode(chosen_mode="EMAIL")`  
  _Use pinned research to reply to pending inquiries._
"""
        except Exception as e:
            log.error(f"💥 UI FOCUS CRASH: {str(e)}")
            return f"❌ **UI ERROR**: Failed to render focus. Details: {str(e)}"
