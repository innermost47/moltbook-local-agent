from typing import Dict
from argparse import Namespace
from src.utils import log
from src.contexts.base_context import BaseContext


class ResearchContext(BaseContext):
    def __init__(self, research_handler, memory_handler):
        self.handler = research_handler
        self.memory = memory_handler

    def get_home_snippet(self) -> str:
        return "🔍 **RESEARCH**: Wikipedia module active"

    def get_list_view(
        self, status_msg: str = "", result: Dict = None, workspace_pins=None
    ) -> str:
        owned_tools = set(self.memory.get_owned_tools())
        search_results = ""
        if result and result.get("success") and "results" in result:
            titles = result["results"]
            search_results = "### 📑 SEARCH RESULTS\n\n"
            for title in titles:
                search_results += f"• `{title}`\n"
            search_results += "\n👉 Use `wiki_read` with one of these titles.\n\n"
        available_actions = []
        locked_actions = []
        if "wiki_search" in owned_tools:
            available_actions.append(
                """
**Step 1**: `wiki_search(query='...', limit=5)`
   - Discover Wikipedia page titles
   - Returns list of matching articles
"""
            )
        else:
            locked_actions.append(
                "🔒 `wiki_search` - 100 XP (unlock to search Wikipedia)"
            )

        if "wiki_read" in owned_tools:
            available_actions.append(
                """
**Step 2**: `wiki_read(page_title='...')`
   - Extract full content from a page
   - Use exact title from search results
"""
            )
        else:
            locked_actions.append("🔒 `wiki_read` - 100 XP (unlock to read articles)")

        if "research_complete" in owned_tools:
            available_actions.append(
                """
**Step 3**: `research_complete(objective='...', findings=[...])`
   - Synthesize and save research findings
   - params: objective, findings (list), is_objective_met
"""
            )
        else:
            locked_actions.append(
                "🔒 `research_complete` - 100 XP (unlock to finalize research)"
            )

        workflow_section = "### 🛠️ RESEARCH WORKFLOW\n\n"

        if available_actions:
            workflow_section += "\n".join(available_actions)
            workflow_section += (
                "\n\n⚠️ **TIP**: Avoid redundant searches. Move step by step."
            )
        else:
            workflow_section += "⚠️ **NO RESEARCH TOOLS UNLOCKED**\n\n"
            workflow_section += "You can't perform Wikipedia research yet.\n"

        if locked_actions:
            workflow_section += "\n\n### 🔒 LOCKED ACTIONS\n"
            workflow_section += "Purchase these tools to unlock research:\n\n"
            workflow_section += "\n".join(locked_actions)
            workflow_section += (
                "\n\n💡 Navigate to HOME and use `visit_shop` to unlock."
            )

        if all(
            t in owned_tools for t in ["wiki_search", "wiki_read", "research_complete"]
        ):
            workflow_section += (
                "\n🎉 **Full research pipeline unlocked!** Search → Read → Complete.\n"
            )

        ctx = [
            "## 🔍 RESEARCH CENTER",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            search_results,
            "---" if search_results else "",
            workflow_section,
        ]

        return "\n".join(ctx)

    def get_focus_view(self, item_id: str) -> str:
        log.debug(f"🔍 Rendering focus view for: '{item_id}'")

        if not item_id or item_id == "None":
            log.warning("⚠️ Focus view called with invalid item_id")
            return """
## ❌ NO TITLE PROVIDED

Please select a valid Wikipedia page title from your search results.

👉 Use `wiki_search` to find titles first.
"""

        try:
            params = Namespace(page_title=item_id)
            result = self.handler.handle_wiki_read(params)

            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                suggestion = result.get("suggestion", "Try a different title.")

                return f"""
## ❌ RESEARCH ERROR

**Title**: `{item_id}`

**Error**: {error_msg}

💡 **Suggestion**: {suggestion}

👉 Use `wiki_search` to find valid titles.
"""

            content = result.get("content", "No content available.")
            source = result.get("source", "live")
            display_title = result.get("title", item_id)
            url = result.get("url", "N/A")

            truncated_content = content[:2000]
            if len(content) > 2000:
                truncated_content += "... *(truncated for display)*"

            return f"""
## 🎯 RESEARCH FOCUS: {display_title.upper()}

**Source**: Wikipedia ({source})
**URL**: {url}

---

### 📄 CONTENT

{truncated_content}

---

### 📌 NEXT STEPS

**Optional notes (recommended if exploring multiple pages)**:
```
pin_to_workspace(
label="research_{display_title[:20]}",
content="[key facts, concepts, or quotes]"
)
```

**Complete research**:
```
research_complete(
    objective="[what you were researching]",
    findings=["finding 1", "finding 2", "finding 3"]
)
```

**Navigate to another mode**:
- `navigate_to_mode(chosen_mode="BLOG")` - Write an article
- `navigate_to_mode(chosen_mode="SOCIAL")` - Share insights
- `navigate_to_mode(chosen_mode="EMAIL")` - Reply with research

---

👉 `wiki_search` - Search for more topics
"""
        except Exception as e:
            log.error(f"💥 Focus view generation failed: {e}")
            return f"""
## ❌ ERROR LOADING PAGE

Could not load Wikipedia page: `{item_id}`

**Details**: {str(e)}

👉 Use `wiki_search` to find valid titles.
"""
