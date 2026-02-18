from datetime import datetime
from src.utils import log
from src.settings import settings


class HomeContext:
    def __init__(
        self,
        mail_ctx,
        blog_ctx,
        social_ctx,
        research_ctx,
        memory_handler,
        progression_system,
    ):
        self.mail = mail_ctx
        self.blog = blog_ctx
        self.social = social_ctx
        self.research = research_ctx
        self.memory = memory_handler
        self.progression = progression_system
        self.has_seen_build_session_strategy_block = False

    def build_home_screen(self, session_id: int) -> str:
        log.info(f"🏠 Assembling Home Dashboard for Session {session_id}...")
        owned_tools = set(self.memory.get_owned_tools())
        active_plan = self.memory.get_active_master_plan()

        if active_plan:
            plan_header = [
                "🗺️ **YOUR MASTER PLAN (Long-Term Objectives)**",
                f"🎯 {active_plan.get('objective')}",
                f"🧠 {active_plan.get('strategy')}",
                f"📍 *Next: {active_plan.get('milestones', ['N/A'])[0] if active_plan.get('milestones') else 'N/A'}*",
                f"{'━' * 40}",
            ]
        else:
            plan_header = [
                "⚠️ **MASTER PLAN REQUIRED**: Define your long-term objectives.\n"
            ]

        session_strategy_block = ""
        if not self.has_seen_build_session_strategy_block:
            session_strategy_block = self._build_session_strategy_block()
            self.has_seen_build_session_strategy_block = True

        prog_status = self.progression.get_current_status()
        owned_tools_count = len(owned_tools)
        progression_block = self._build_progression_block(
            prog_status, owned_tools_count, owned_tools
        )

        recent_learnings = self.memory.get_recent_learnings(limit=3)

        recap_block = []
        if recent_learnings:
            feedback_intro = (
                "📢 **SESSION LEARNINGS EXPLANATION**\n"
                "This block represents a summary of your recent sessions. "
                "Each session includes the date and the learnings recorded at the end. "
                "It is **important and mandatory** that you read and consider these learnings "
                "so that you can improve your performance, diversify your actions, "
                "and make better decisions in the next sessions.\n"
            )
            recap_block.append(feedback_intro)

            for session in recent_learnings:
                try:
                    dt = datetime.fromisoformat(session["date"])
                    formatted_date = dt.strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    formatted_date = session["date"]

                recap_block.append(f"📅 **Session Date:** {formatted_date}")
                recap_block.append("")
                recap_block.append(session["learnings"])
                recap_block.append("---\n")

        memory_entries_display = self._build_memory_entries_block()
        cached_topics_display = self._build_cached_research_block()

        dashboard = ["## 🏠 AGENT HOME DASHBOARD", "\n".join(plan_header), ""]
        dashboard.append(session_strategy_block)
        dashboard.append("")
        dashboard.append(progression_block)
        dashboard.append("")
        dashboard.extend(recap_block)

        if memory_entries_display:
            dashboard.append(memory_entries_display)
            dashboard.append("")

        if cached_topics_display:
            dashboard.append(cached_topics_display)
            dashboard.append("")

        dashboard += [
            "### 🛠️ SESSION CONSTRAINTS",
            f"⚡ **LIMIT**: {settings.MAX_ACTIONS_PER_SESSION} ACTIONS MAX.",
            "⚖️ **PRIORITY**: Handle direct interactions (Mail/Blog) first, then diversify.",
            "🎯 **STRATEGY**: Balance across Email, Blog, Social, Research, Memory.",
        ]
        dashboard.append(self._build_available_actions_block(owned_tools))
        return "\n".join(dashboard)

    def _build_available_actions_block(self, owned_tools: set) -> str:

        available = []
        locked = []

        available.append("👉 `navigate_to_mode` - Navigate to other modules")

        if "pin_to_workspace" in owned_tools:
            available.append("👉 `pin_to_workspace` - Pin important info")

        if "memory_store" in owned_tools:
            available.append("👉 `memory_store` - Save insights")
        else:
            locked.append("🔒 `memory_store` - 100 XP")

        if "memory_retrieve" in owned_tools:
            available.append("👉 `memory_retrieve` - Read saved notes")
        else:
            locked.append("🔒 `memory_retrieve` - 100 XP")

        available.append("👉 `visit_shop` - Browse tools & artifacts")

        actions_block = [
            "### 🎯 AVAILABLE ACTIONS (HOME)",
            "",
            "**✅ You can use:**",
        ]

        actions_block.extend(available)

        if locked:
            actions_block.append("")
            actions_block.append("**🔒 Locked (visit shop to unlock):**")
            actions_block.extend(locked)

        actions_block.append("")
        actions_block.append(
            "💡 Use `visit_shop` to see all available tools and artifacts"
        )
        actions_block.append(f"{'━' * 40}")

        memory_full = "memory_store" in owned_tools and "memory_retrieve" in owned_tools
        if memory_full:
            available.append("✅ **Full memory access** — store & retrieve")

        return "\n".join(actions_block)

    def _build_session_strategy_block(self) -> str:
        strategy_block = [
            "### 📋 SESSION PLANNING WORKFLOW",
            "",
            "**💡 RECOMMENDED FIRST ACTION: Create your session to-do list**",
            "",
            "Use `pin_to_workspace` to organize your priorities and keep them visible.",
            "",
            "✅ **Benefits:**",
            "• Prevents loops - you have a clear roadmap visible at all times",
            "• Stays pinned at the top of EVERY screen you visit",
            "• Easy to update: just `pin_to_workspace` again with updated content",
            "• Use `unpin_from_workspace(label='SESSION_TODO')` to remove when done",
            "",
            "💡 **Pro tip:** Update your plan as you complete tasks to track progress!",
            "",
            f"{'━' * 40}",
        ]

        return "\n".join(strategy_block)

    def _build_progression_block(
        self, prog_status: dict, owned_tools_count: int = 99, owned_tools: set = None
    ) -> str:
        owned_tools = owned_tools or set()
        if not prog_status:
            return ""

        level = prog_status.get("level", 1)
        total_xp_earned = prog_status.get("total_xp_earned", 0)
        current_xp_balance = prog_status.get("current_xp_balance", 0)
        xp_needed = prog_status.get("xp_needed", 100)
        xp_progress_in_level = prog_status.get("xp_progress_in_level", 0)
        title = prog_status.get("current_title", "🌱 Digital Seedling")
        badges = prog_status.get("badges", [])
        progress_pct = prog_status.get("progress_percentage", 0)

        bar_width = 30
        filled = int(bar_width * (progress_pct / 100))
        empty = bar_width - filled
        xp_bar = "█" * filled + "░" * empty

        badge_display = ""
        if badges:
            badge_icons = " ".join([b["icon"] for b in badges[:5]])
            badge_count = len(badges)
            badge_display = (
                f"\n🏆 **Badges Unlocked**: {badge_icons} ({badge_count} total)"
            )

        is_early_game = owned_tools_count <= 6

        if is_early_game:
            xp_actions = []

            if "write_blog_article" in owned_tools:
                xp_actions.append("• ✅ `write_blog_article`: **+25 XP** ← BEST ROI")
            if "create_post" in owned_tools:
                xp_actions.append("• ✅ `create_post`: **+15 XP**")
            if "share_link" in owned_tools:
                xp_actions.append("• ✅ `share_link`: **+12 XP**")
            if "comment_post" in owned_tools:
                xp_actions.append(
                    "• ✅ `comment_post`: **+10 XP** (on DIFFERENT posts)"
                )
            if "email_send" in owned_tools:
                xp_actions.append("• ✅ `email_send`: **+10 XP**")
            if "memory_store" in owned_tools:
                xp_actions.append("• ✅ `memory_store`: **+7 XP**")

            xp_earning_section = [
                "💡 **How to Earn XP (your available actions, best ROI first):**",
                *xp_actions,
                "• 🎯 Use the highest XP action available to you right now!",
            ]
            penalty_section = [
                "⚠️ **XP PENALTIES** (only for navigation/utility loops):",
                "• Repeating `navigate_to_mode` or `refresh_home` → XP penalty",
                "• ✅ Repeating `comment_post` on different posts → NO penalty (encouraged!)",
                f"{'━' * 40}",
            ]
        else:
            xp_earning_section = [
                "💡 **How to Earn XP:**",
                "• Major actions: Write blog (25 XP), Complete research (40 XP)",
                "• Medium actions: Send email (10 XP), Create post (15 XP), Share link (12 XP)",
                "• Small actions: Comment (10 XP), Store memory (7 XP), Vote (3 XP)",
                "• Special bonuses: Perfect session (100 XP), Engagement master (50 XP)",
                "• Each XP earned increases BOTH your Balance AND your Total",
            ]
            penalty_section = [
                "⚠️ **XP PENALTIES FOR LOOPS:**",
                "• Penalties reduce your XP Balance (not your Total or Level)",
                "• 2nd repeat: -10 XP | 3rd repeat: -20 XP | 4th repeat: -30 XP",
                "• 5th+ repeat: -50 XP, -75 XP, -100 XP",
                "• STOP wasting actions = STOP losing XP Balance!",
                f"{'━' * 40}",
            ]

        progression_block = [
            "### 🎮 PROGRESSION & ACHIEVEMENTS",
            f"**Level {level}** - {title}",
            f"Progress to Next Level: [{xp_bar}] {xp_progress_in_level}/{xp_needed} ({progress_pct:.1f}%)",
            f"Total XP Earned: {total_xp_earned:,} (determines your level)",
            f"XP Balance: {current_xp_balance:,} (available for shop)",
            badge_display if badge_display else "",
            "\n",
            "🎯 **WHY EARN XP?**",
            "• XP Balance is your CURRENCY to unlock new capabilities",
            "• All tools cost 100 XP in the shop (write_blog, email_send, wiki_search, etc.)",
            "• 💡 **IMPORTANT**: Buying tools uses your XP Balance but does NOT affect:",
            "  - Your Total XP Earned (permanent)",
            "  - Your Level (permanent)",
            "  - Your Progress Bar (based on Total XP Earned)",
            "• More tools = More strategic options = Better performance",
            "• Use `visit_shop` to browse available tools and purchase with XP Balance",
            "\n",
            *xp_earning_section,
            "\n",
            *penalty_section,
        ]

        return "\n".join([line for line in progression_block if line])

    def _build_memory_entries_block(self) -> str:
        try:
            owned_tools = set(self.memory.get_owned_tools())
            has_memory_retrieve = "memory_retrieve" in owned_tools
            has_memory_store = "memory_store" in owned_tools

            cursor = self.memory.conn.cursor()
            cursor.execute(
                "SELECT DISTINCT category FROM memory_entries ORDER BY category"
            )
            categories = [row["category"] for row in cursor.fetchall()]

            if not categories:
                if not has_memory_store:
                    return (
                        "## 💾 MEMORY ARCHIVE\n\n"
                        "⚠️ **No memories stored yet.**\n"
                        "🔒 You need to unlock `memory_store` (100 XP) to save memories.\n"
                        "💡 Use `visit_shop` to purchase this tool.\n"
                    )
                else:
                    return (
                        "## 💾 MEMORY ARCHIVE\n\n"
                        "⚠️ **No memories stored yet.** Use `memory_store` to save insights, experiments, and learnings.\n"
                    )

            memory_block = ["## 💾 MEMORY ARCHIVE (Last 5 per Category)", ""]
            total_entries = 0

            for category in categories:
                cursor.execute(
                    """
                    SELECT content, created_at 
                    FROM memory_entries 
                    WHERE category = ? 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """,
                    (category,),
                )

                entries = cursor.fetchall()

                if entries:
                    memory_block.append(
                        f"### 📂 {category.upper()} ({len(entries)} recent)"
                    )

                    for entry in entries:
                        content = entry["content"]
                        truncated = (
                            content[:500] + "..." if len(content) > 500 else content
                        )

                        try:
                            dt = datetime.fromisoformat(entry["created_at"])
                            date_str = dt.strftime("%d/%m %H:%M")
                        except:
                            date_str = entry["created_at"][:10]

                        memory_block.append(f"• [{date_str}] {truncated}")

                    memory_block.append("")
                    total_entries += len(entries)

            if total_entries > 0:
                memory_block.insert(
                    1,
                    f"**Total displayed**: {total_entries} entries across {len(categories)} categories",
                )

                if has_memory_store and has_memory_retrieve:
                    memory_block.insert(
                        2,
                        "⚠️ **ANTI-DUPLICATION**: These memories are ALREADY stored. Do NOT store duplicates.\n"
                        "💡 **TIP**: Use `memory_retrieve(category='...')` to see full content.\n",
                    )
                elif has_memory_store and not has_memory_retrieve:
                    memory_block.insert(
                        2,
                        "⚠️ **ANTI-DUPLICATION**: These memories are ALREADY stored. Do NOT store duplicates.\n"
                        "🔒 Unlock `memory_retrieve` (100 XP) to read full memory content.\n",
                    )
                elif not has_memory_store and has_memory_retrieve:
                    memory_block.insert(
                        2,
                        "💡 **TIP**: Use `memory_retrieve(category='...')` to see full content.\n"
                        "🔒 Unlock `memory_store` (100 XP) to save new memories.\n",
                    )
                else:
                    memory_block.insert(
                        2,
                        "🔒 Unlock `memory_store` and `memory_retrieve` (100 XP each) to manage memories.\n",
                    )

                return "\n".join(memory_block)

            return ""

        except Exception as e:
            log.error(f"Failed to build memory entries block: {e}")
            return "## 💾 MEMORY ARCHIVE\n\n⚠️ Error loading memories.\n"

    def _build_cached_research_block(self) -> str:
        try:
            owned_tools = set(self.memory.get_owned_tools())
            has_wiki_search = "wiki_search" in owned_tools
            has_wiki_read = "wiki_read" in owned_tools
            if not hasattr(self.research, "handler"):
                log.debug("Research context has no handler attribute")
                return ""

            handler = self.research.handler

            if not hasattr(handler, "vector_db"):
                log.debug("Research handler has no vector_db attribute")
                return ""

            vector_db = handler.vector_db

            all_docs = vector_db.get()

            log.debug(f"Vector DB get() returned: {type(all_docs)}")
            log.debug(f"Keys in all_docs: {all_docs.keys() if all_docs else 'None'}")

            if not all_docs:
                if not has_wiki_search or not has_wiki_read:
                    locked = []
                    if not has_wiki_search:
                        locked.append("`wiki_search`")
                    if not has_wiki_read:
                        locked.append("`wiki_read`")

                    return (
                        "## 🔍 RESEARCH CACHE\n\n"
                        f"⚠️ **No research cached yet.**\n"
                        f"🔒 You need to unlock {' and '.join(locked)} (100 XP each) to research Wikipedia.\n"
                        "💡 Use `visit_shop` to purchase these tools.\n"
                    )
                else:
                    return (
                        "## 🔍 RESEARCH CACHE\n\n"
                        "⚠️ **No research cached yet.** Use `wiki_search` and `wiki_read` to build knowledge.\n"
                    )

            metadatas = all_docs.get("metadatas")

            if not metadatas:
                log.warning(f"No metadatas in vector DB result: {all_docs.keys()}")
                return (
                    "## 🔍 RESEARCH CACHE\n\n"
                    "⚠️ **Cache structure issue.** Try running `wiki_read` to populate cache.\n"
                )

            log.info(f"Found {len(metadatas)} metadata entries in vector DB")

            topics = {}

            for metadata in metadatas:
                if isinstance(metadata, dict):
                    title = metadata.get("title", "Unknown")
                    url = metadata.get("url", "")

                    if title and title != "Unknown":
                        topics[title] = url

            log.info(f"Extracted {len(topics)} unique topics from cache")

            if not topics:
                return (
                    "## 🔍 RESEARCH CACHE\n\n"
                    "⚠️ **No valid topics found in cache.** Use `wiki_read` to add Wikipedia pages.\n"
                )

            research_block = [
                "## 🔍 RESEARCH CACHE (Already Searched Topics)",
                "",
                f"**Total cached pages**: {len(topics)}",
            ]

            if has_wiki_search and has_wiki_read:
                research_block.append(
                    "⚠️ **ANTI-DUPLICATION**: These Wikipedia pages are ALREADY cached. Do NOT search them again.\n"
                    "💡 **TIP**: Use `research_query_cache(query='topic')` to retrieve cached content.\n"
                )
            else:
                locked = []
                if not has_wiki_search:
                    locked.append("`wiki_search`")
                if not has_wiki_read:
                    locked.append("`wiki_read`")
                research_block.append(
                    f"🔒 Unlock {' and '.join(locked)} (100 XP each) to add more research.\n"
                )

            sorted_topics = sorted(topics.keys())[:15]

            for title in sorted_topics:
                research_block.append(f"• **{title}** (cached)")

            if len(topics) > 15:
                research_block.append(
                    f"\n... and {len(topics) - 15} more topics in cache"
                )

            research_block.append("")

            return "\n".join(research_block)

        except Exception as e:
            log.error(f"Failed to build cached research block: {e}", exc_info=True)
            return ""
