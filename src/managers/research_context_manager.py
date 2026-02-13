from typing import Dict
from argparse import Namespace
from src.utils import log


class ResearchContextManager:
    def __init__(self, research_handler):
        self.handler = research_handler

    def get_home_snippet(self) -> str:
        return "🔍 **RESEARCH**: Wikipedia module active"

    def get_list_view(self, status_msg: str = "", result: Dict = None) -> str:
        action_feedback = ""

        if result:
            if result.get("success"):
                if "results" in result:
                    titles = result["results"]
                    action_feedback = "### 📑 SEARCH RESULTS\n\n"
                    for title in titles:
                        action_feedback += f"• `{title}`\n"
                    action_feedback += (
                        "\n👉 Use `wiki_read` with one of these titles.\n\n---\n"
                    )
                else:
                    action_feedback = (
                        f"### ✅ LAST ACTION SUCCESS\n{result.get('data')}\n\n---\n"
                    )
            else:
                if result.get("visual_feedback"):
                    action_feedback = f"### 🔴 LAST ACTION FAILED\n{result['visual_feedback']}\n\n---\n"
                else:
                    action_feedback = f"### ❌ LAST ACTION ERROR\n{result.get('error', 'Unknown error')}\n\n💡 {result.get('suggestion', 'Try again.')}\n\n---\n"

        ctx = [
            "## 🔍 RESEARCH CENTER",
            f"✅ **STATUS**: {status_msg}" if status_msg else "",
            "---",
            action_feedback if action_feedback else "_No active research data._\n",
            "---",
            "### 🛠️ RESEARCH WORKFLOW",
            "",
            "**Step 1**: `wiki_search`",
            "   - **params**: `query`, `limit` (optional, default 5)",
            "   - Discover Wikipedia page titles",
            "",
            "**Step 2**: `wiki_read`",
            "   - **params**: `page_title` (exact title from search)",
            "   - Extract full content from a page",
            "",
            "**Step 3**: `research_complete`",
            "   - **params**: `objective`, `findings` (list), `is_objective_met`",
            "   - Synthesize and save findings to workspace",
            "",
            "---",
            "",
            "⚠️ **TIP**: Avoid redundant searches. If you have titles, move to `wiki_read`.",
            "",
            "👉 `refresh_home` - Return to dashboard",
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
🏠 Use `refresh_home` to return.
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
🏠 Use `refresh_home` to return.
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

**Save to workspace**:
```
pin_to_workspace(label="research_{display_title[:20]}", content="[your key findings]")
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
🏠 `refresh_home` - Return to dashboard
"""
        except Exception as e:
            log.error(f"💥 Focus view generation failed: {e}")
            return f"""
## ❌ ERROR LOADING PAGE

Could not load Wikipedia page: `{item_id}`

**Details**: {str(e)}

👉 Use `wiki_search` to find valid titles.
🏠 Use `refresh_home` to return.
"""
