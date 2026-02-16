from typing import Dict
from src.contexts.base_context import BaseContext


class ShopContext(BaseContext):
    def __init__(self, memory_handler, progression_system):
        self.memory = memory_handler
        self.progression = progression_system

    def get_home_snippet(self) -> str:
        return "🛒 **SHOP**: Tools & Artifacts marketplace"

    def get_list_view(
        self, status_msg: str = "", result: Dict = None, workspace_pins=None
    ) -> str:

        owned_tools = set(self.memory.get_owned_tools())
        prog_status = self.progression.get_current_status()
        current_xp_balance = prog_status.get("current_xp_balance", 0)
        total_xp_earned = prog_status.get("total_xp_earned", 0)

        catalog = self.memory.get_shop_catalog()
        tools = catalog.get("tools", [])

        categories = {
            "social": [],
            "blog": [],
            "email": [],
            "research": [],
            "memory": [],
            "navigation": [],
        }

        for tool in tools:
            cat = tool.get("category", "other")
            if cat in categories:
                categories[cat].append(tool)

        shop_display = []

        shop_display.append("## 🛒 ARTIFACT SHOP")
        shop_display.append("")
        shop_display.append(
            f"💰 **XP Balance**: {current_xp_balance} XP (available to spend)"
        )
        shop_display.append(
            f"📊 **Total XP Earned**: {total_xp_earned:,} XP (all-time)"
        )
        shop_display.append(
            f"🎯 **Level**: {prog_status.get('level', 1)} - {prog_status.get('current_title', 'Digital Seedling')}"
        )
        shop_display.append("")
        shop_display.append(
            "💡 **Spending XP on tools does NOT affect your level or total XP earned!**"
        )
        shop_display.append("")
        shop_display.append("━" * 60)
        shop_display.append("")

        shop_display.append("## 🛠️ AVAILABLE TOOLS")
        shop_display.append("")
        shop_display.append("**All tools cost 100 XP** (unless marked FREE)")
        shop_display.append("")

        total_locked = 0

        for category_name, display_name in [
            ("social", "📱 SOCIAL (Moltbook)"),
            ("blog", "✍️ BLOG"),
            ("email", "📧 EMAIL"),
            ("research", "🔍 RESEARCH (Wikipedia)"),
            ("memory", "🧠 MEMORY"),
            ("navigation", "🧭 NAVIGATION"),
        ]:
            cat_tools = categories.get(category_name, [])
            if not cat_tools:
                continue

            shop_display.append(f"### {display_name}")
            shop_display.append("")

            for tool in cat_tools:
                tool_name = tool.get("tool_name")
                price = tool.get("price", 100)
                description = tool.get("description", "")
                is_starter = tool.get("is_starter", False)
                owned = tool_name in owned_tools

                if owned:
                    shop_display.append(f"  ✅ **{tool_name}** - OWNED")
                    shop_display.append(f"     _{description}_")
                elif is_starter:
                    shop_display.append(f"  🎁 **{tool_name}** - FREE (starter tool)")
                    shop_display.append(f"     _{description}_")
                    shop_display.append(f"     👉 Already unlocked for you!")
                else:
                    affordable = current_xp_balance >= price
                    icon = "💰" if affordable else "🔒"

                    shop_display.append(f"  {icon} **{tool_name}** - {price} XP")
                    shop_display.append(f"     _{description}_")

                    if affordable:
                        shop_display.append(
                            f'     👉 `buy_tool(tool_name="{tool_name}")`'
                        )
                    else:
                        needed = price - current_xp_balance
                        shop_display.append(f"     ⚠️ Need {needed} more XP")

                    total_locked += 1

                shop_display.append("")

        shop_display.append("━" * 60)
        shop_display.append("")

        total_tools = len(tools)
        owned_count = len(owned_tools)

        shop_display.append("## 📊 YOUR PROGRESSION")
        shop_display.append("")
        shop_display.append(f"**Tools Owned**: {owned_count}/{total_tools}")
        shop_display.append(
            f"**Tools Available**: {total_locked} tools ready to unlock"
        )
        shop_display.append(f"**XP Balance**: {current_xp_balance}")
        shop_display.append("")

        if current_xp_balance >= 100:
            shop_display.append("## 💡 RECOMMENDATIONS")
            shop_display.append("")

            if "create_post" not in owned_tools and "social" in categories:
                shop_display.append(
                    "🎯 **High Priority**: `create_post` - Start creating content on Moltbook"
                )

            if "write_blog_article" not in owned_tools and "blog" in categories:
                shop_display.append(
                    "🎯 **High Value**: `write_blog_article` - Create long-form content (+25 XP per article)"
                )

            if "email_read" not in owned_tools and "email" in categories:
                shop_display.append(
                    "🎯 **Communication**: `email_read` - Read your emails"
                )

            if "wiki_search" not in owned_tools and "research" in categories:
                shop_display.append(
                    "🎯 **Knowledge**: `wiki_search` - Research topics for content"
                )

            shop_display.append("")

        shop_display.append("━" * 60)
        shop_display.append("")

        shop_display.append("## 🛠️ AVAILABLE ACTIONS")
        shop_display.append("")
        shop_display.append('👉 `buy_tool(tool_name="...")`')
        shop_display.append("   - Purchase a tool with your XP Balance")
        shop_display.append("   - Use exact tool_name from list above")
        shop_display.append("   - Your level won't change when you buy!")
        shop_display.append("")
        shop_display.append('👉 `navigate_to_mode(chosen_mode="HOME")`')
        shop_display.append("   - Return to dashboard")
        shop_display.append("")
        shop_display.append("💡 **Strategy Tips:**")
        shop_display.append("- Tools unlock NEW capabilities (real Python functions)")
        shop_display.append("- All tools cost 100 XP (fair pricing)")
        shop_display.append("- Buying tools uses XP Balance (not Total XP or Level)")
        shop_display.append("- Prioritize tools that help you EARN more XP")
        shop_display.append("- Blog tools = high XP return (25 XP per article)")
        shop_display.append("- Social tools = engagement & community building")
        shop_display.append("")

        if total_locked == 0:
            shop_display.append("🎉 **CONGRATULATIONS! You own ALL available tools!**")
            shop_display.append("")

        return "\n".join(shop_display)

    def get_focus_view(self, item_id: str) -> str:

        owned_tools = set(self.memory.get_owned_tools())
        prog_status = self.progression.get_current_status()
        current_xp_balance = prog_status.get("current_xp_balance", 0)

        catalog = self.memory.get_shop_catalog()
        tools = catalog.get("tools", [])

        tool = None
        for t in tools:
            if t.get("tool_name") == item_id:
                tool = t
                break

        if not tool:
            return f"""
## ❌ TOOL NOT FOUND

**Tool**: `{item_id}`

This tool doesn't exist in the shop catalog.

👉 Use `navigate_to_mode(chosen_mode="SHOP")` to see available tools.
"""

        tool_name = tool.get("tool_name")
        category = tool.get("category", "other")
        price = tool.get("price", 100)
        description = tool.get("description", "")
        is_starter = tool.get("is_starter", False)
        owned = tool_name in owned_tools

        detail = []

        detail.append(f"## 🎯 TOOL DETAILS: {tool_name}")
        detail.append("")
        detail.append(f"**Category**: {category.upper()}")
        detail.append(
            f"**Price**: {price} XP" + (" (FREE starter)" if is_starter else "")
        )
        detail.append(f"**Status**: {'✅ OWNED' if owned else '🔒 LOCKED'}")
        detail.append("")
        detail.append("━" * 60)
        detail.append("")
        detail.append("### 📝 DESCRIPTION")
        detail.append("")
        detail.append(description)
        detail.append("")
        detail.append("━" * 60)
        detail.append("")

        use_cases = {
            "create_post": "Share thoughts, start discussions, engage community",
            "share_link": "Share blog articles, external content, resources",
            "write_blog_article": "Create long-form content, build authority, earn XP",
            "email_send": "Reply to messages, network with others",
            "wiki_search": "Research topics for blog posts, gather knowledge",
            "memory_store": "Save insights, track learnings, build knowledge base",
        }

        if tool_name in use_cases:
            detail.append("### 💡 USE CASES")
            detail.append("")
            detail.append(use_cases[tool_name])
            detail.append("")
            detail.append("━" * 60)
            detail.append("")

        xp_values = {
            "write_blog_article": "+25 XP per article (pays for itself in 4 uses)",
            "create_post": "+15 XP per post (pays for itself in 7 uses)",
            "share_link": "+12 XP per share (pays for itself in 9 uses)",
            "email_send": "+10 XP per email (pays for itself in 10 uses)",
            "wiki_search": "+10 XP per search (pays for itself in 10 uses)",
        }

        if tool_name in xp_values:
            detail.append("### 📊 XP RETURN ON INVESTMENT")
            detail.append("")
            detail.append(xp_values[tool_name])
            detail.append("")
            detail.append("━" * 60)
            detail.append("")

        detail.append("### 🛠️ ACTIONS")
        detail.append("")

        if owned:
            detail.append("✅ **You already own this tool!**")
            detail.append("")
            detail.append("You can use it in the appropriate module.")
        elif is_starter:
            detail.append("🎁 **This is a FREE starter tool!**")
            detail.append("")
            detail.append("It should already be unlocked for you.")
        else:
            affordable = current_xp_balance >= price

            if affordable:
                detail.append(f'👉 `buy_tool(tool_name="{tool_name}")`')
                detail.append(f"   - Purchase this tool for {price} XP")
                detail.append(
                    f"   - Remaining balance: {current_xp_balance - price} XP"
                )
                detail.append(f"   - Your level won't change!")
            else:
                needed = price - current_xp_balance
                detail.append(f"⚠️ **Insufficient XP Balance**")
                detail.append("")
                detail.append(f"You need {needed} more XP to purchase this tool.")
                detail.append("")
                detail.append("💡 **How to earn XP:**")
                detail.append("- Use your existing tools to complete actions")
                detail.append("- Diversify across modules (Email, Blog, Social)")
                detail.append("- Avoid loops (they reduce your XP Balance!)")

        detail.append("")
        detail.append('👉 `navigate_to_mode(chosen_mode="SHOP")`')
        detail.append("   - Return to shop catalog")
        detail.append("")

        return "\n".join(detail)
