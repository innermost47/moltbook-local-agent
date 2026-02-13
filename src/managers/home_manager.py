from datetime import datetime
from src.utils import log
from src.settings import settings


class HomeManager:
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

    def build_home_screen(self, session_id: int) -> str:
        log.info(f"🏠 Assembling Home Dashboard for Session {session_id}...")

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

        prog_status = self.progression.get_current_status()
        progression_block = self._build_progression_block(prog_status)

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
        dashboard.append(progression_block)
        dashboard.append("")
        dashboard.extend(recap_block)

        dashboard += [
            "### 🔔 LIVE NOTIFICATIONS",
            self.mail.get_home_snippet(),
            self.blog.get_home_snippet(),
            self.social.get_home_snippet(),
            "",
        ]

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

        return "\n".join(dashboard)

    def _build_progression_block(self, prog_status: dict) -> str:
        if not prog_status:
            return ""

        level = prog_status.get("level", 1)
        current_xp = prog_status.get("current_xp", 0)
        xp_needed = prog_status.get("xp_needed", 100)
        total_xp = prog_status.get("total_xp", 0)
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

        progression_block = [
            "### 🎮 PROGRESSION & ACHIEVEMENTS",
            f"**Level {level}** - {title}",
            f"XP: [{xp_bar}] {current_xp}/{xp_needed} ({progress_pct:.1f}%)",
            f"Total XP Earned: {total_xp:,}",
            badge_display if badge_display else "",
            "\n",
            "💡 **How to Earn XP:**",
            "• Major actions: Write blog (25 XP), Complete research (40 XP)",
            "• Medium actions: Send email (10 XP), Create post (15 XP), Share link (12 XP)",
            "• Small actions: Comment (8 XP), Store memory (7 XP), Vote (3 XP)",
            "• Special bonuses: Perfect session (100 XP), Engagement master (50 XP)",
            f"{'━' * 40}",
        ]

        return "\n".join([line for line in progression_block if line])

    def _build_memory_entries_block(self) -> str:
        try:
            cursor = self.memory.conn.cursor()

            cursor.execute(
                "SELECT DISTINCT category FROM memory_entries ORDER BY category"
            )
            categories = [row["category"] for row in cursor.fetchall()]

            if not categories:
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
                memory_block.insert(
                    2,
                    "⚠️ **ANTI-DUPLICATION**: These memories are ALREADY stored. Do NOT store duplicates.\n"
                    "💡 **TIP**: Use `memory_retrieve(category='...')` to see full content.\n",
                )
                return "\n".join(memory_block)

            return ""

        except Exception as e:
            log.error(f"Failed to build memory entries block: {e}")
            return "## 💾 MEMORY ARCHIVE\n\n⚠️ Error loading memories.\n"

    def _build_cached_research_block(self) -> str:
        try:
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
                log.warning("Vector DB returned None or empty")
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
                "⚠️ **ANTI-DUPLICATION**: These Wikipedia pages are ALREADY cached. Do NOT search them again.\n"
                "💡 **TIP**: Use `research_query_cache(query='topic')` to retrieve cached content.\n",
            ]

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
