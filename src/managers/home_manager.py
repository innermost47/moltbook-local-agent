from typing import List
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
                "🗺️ **STRATEGIC ALIGNMENT**",
                f"🎯 {active_plan.get('objective')}",
                f"🧠 {active_plan.get('strategy')}",
                f"📍 *Next: {active_plan.get('milestones', ['N/A'])[0] if active_plan.get('milestones') else 'N/A'}*",
                "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈",
            ]
        else:
            plan_header = ["⚠️ **ALIGNMENT REQUIRED**: Define Master Plan."]

        recent_learnings = self.memory.get_recent_learnings(limit=3)

        recap_block = []
        if recent_learnings:
            recap_block.append("📜 **RECENT SESSION LEARNINGS**")
            for i, learning in enumerate(recent_learnings, 1):
                recap_block.append(f"{i}. {learning.strip()}")
            recap_block.append("")

        dashboard = ["## 🏠 AGENT HOME DASHBOARD", "\n".join(plan_header), ""]
        dashboard.extend(recap_block)

        dashboard += [
            "### 🔔 LIVE NOTIFICATIONS",
            self.mail.get_home_snippet(),
            self.blog.get_home_snippet(),
            self.social.get_home_snippet(),
            "",
            "### 🧠 INTERNAL KNOWLEDGE",
            self.research.get_home_snippet(),
            self.memory.get_agent_context_snippet(),
            "",
            "### 🛠️ SESSION CONSTRAINTS",
            f"⚡ **LIMIT**: {settings.MAX_ACTIONS_PER_SESSION} ACTIONS MAX.",
            "⚖️ **PRIORITY**: Handle direct interactions (Mail/Blog) first.",
        ]

        return "\n".join(dashboard)
