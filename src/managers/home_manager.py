from datetime import datetime
from src.utils import log
from src.settings import settings


class HomeManager:
    def __init__(self, mail_ctx, blog_ctx, social_ctx, research_ctx, memory_handler):
        self.mail = mail_ctx
        self.blog = blog_ctx
        self.social = social_ctx
        self.research = research_ctx
        self.memory = memory_handler

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
            "### 🧠 INTERNAL KNOWLEDGE SUMMARY",
            self.memory.get_agent_context_snippet(),
            "",
            "### 🛠️ SESSION CONSTRAINTS",
            f"⚡ **LIMIT**: {settings.MAX_ACTIONS_PER_SESSION} ACTIONS MAX.",
            "⚖️ **PRIORITY**: Handle direct interactions (Mail/Blog) first.",
        ]

        return "\n".join(dashboard)

    def _build_memory_entries_block(self) -> str:
        try:
            cursor = self.memory.conn.cursor()

            cursor.execute(
                "SELECT DISTINCT category FROM memory_entries ORDER BY category"
            )
            categories = [row["category"] for row in cursor.fetchall()]

            if not categories:
                return ""

            memory_block = ["## 💾 STORED MEMORIES (Last 5 per Category)", ""]

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
                            content[:100] + "..." if len(content) > 100 else content
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
                    "⚠️ **IMPORTANT**: You already have these memories stored. Do NOT store duplicates. Use `memory_retrieve` to see full content.\n",
                )
                return "\n".join(memory_block)

            return ""

        except Exception as e:
            log.error(f"Failed to build memory entries block: {e}")
            return ""

    def _build_cached_research_block(self) -> str:
        try:
            if not hasattr(self.research, "vector_db"):
                return ""

            all_docs = self.research.handler.vector_db.get()

            if not all_docs or not all_docs.get("metadatas"):
                return ""

            topics = {}

            for metadata in all_docs["metadatas"]:
                title = metadata.get("title", "Unknown")
                url = metadata.get("url", "")

                if title not in topics:
                    topics[title] = url

            if not topics:
                return ""

            research_block = [
                "## 🔍 CACHED RESEARCH (Already Searched Topics)",
                "",
                f"**Total cached pages**: {len(topics)}",
                "⚠️ **IMPORTANT**: These topics are ALREADY in your knowledge cache. Do NOT search Wikipedia for them again - use `research_query_cache` or `memory_retrieve` instead.\n",
            ]

            sorted_topics = sorted(topics.keys())[:15]

            for title in sorted_topics:
                research_block.append(f"• **{title}** (cached)")

            if len(topics) > 15:
                research_block.append(
                    f"\n... and {len(topics) - 15} more topics in cache"
                )

            research_block.append("")
            research_block.append(
                "💡 **TIP**: To query cache, use `research_query_cache(query='topic')`"
            )

            return "\n".join(research_block)

        except Exception as e:
            log.error(f"Failed to build cached research block: {e}")
            return ""
