from typing import Optional, Dict
from src.settings import settings


class UIUtils:

    @staticmethod
    def render_navbar(current_domain: str, action_count: int) -> str:
        terminal_label = "📡 SYSTEM TERMINAL"
        node_status = f"NODE: {current_domain.upper()}"

        width = 40
        padding = width - len(terminal_label)
        top_line = f"**{terminal_label}{node_status.rjust(padding)}**"

        nav_items = [
            (
                f"📍 ▶️ **[{d.upper()}]**"
                if d.lower() == current_domain.lower()
                else d.upper()
            )
            for d in settings.AVAILABLE_MODULES
        ]

        max_actions = settings.MAX_ACTIONS_PER_SESSION
        remaining = max_actions - action_count
        energy_bar = "🟢" * remaining + "🔴" * action_count

        return (
            f"{top_line}\n"
            f"{'━' * width}\n"
            f"🌐 {' | '.join(nav_items)}\n"
            f"🔋 {energy_bar} ({remaining}/{max_actions} actions left)\n"
            f"{'━' * width}"
        )

    @staticmethod
    def render_feedback(
        success_msg: Optional[str] = None, error_msg: Optional[str] = None
    ) -> str:
        feedback = ""
        if success_msg:
            feedback += f"\n✅ **LAST STATUS**: {success_msg}\n"
            feedback += "⚠️ IMPORTANT AND HIGH-PRIORITY: DO NOT REPEAT THIS STEP. MOVE IMMEDIATELY TO THE NEXT TASK.\n"

        if error_msg:
            feedback += f"\n❌ **LAST STATUS**: {error_msg}\n"
            feedback += "⚠️ CRITICAL AND MANDATORY: CORRECT THIS ERROR IMMEDIATELY BEFORE PROCEEDING.\n"

        if feedback:
            feedback += f"{'━' * 40}"

        return feedback

    @staticmethod
    def render_footer() -> str:
        return (
            f"{'━' * 40}\n"
            "🎮 **GLOBAL SHORTCUTS**\n"
            "🏠 `refresh_home` | 🧠 `memory_list` | 🗺️ `plan_update` | 🔌 `archive_session`"
        )

    @classmethod
    def layout(
        cls,
        content: str,
        current_domain: str = "HOME",
        action_count: int = 0,
        success_msg: str = None,
        error_msg: str = None,
    ) -> str:
        header = cls.render_navbar(current_domain, action_count)
        notifications = cls.render_feedback(success_msg, error_msg)
        body = content
        footer = cls.render_footer()

        return f"{header}\n{notifications}\n\n{body}\n\n{footer}"

    @staticmethod
    def render_workspace(workspace_data: Dict[str, str]) -> str:
        if not workspace_data:
            return ""

        total_chars = sum(len(v) for v in workspace_data.values())
        is_heavy = total_chars > 2000

        ws = ["📋 **WORKSPACE (Pinned Data)**"]
        if is_heavy:
            ws.append(
                "⚠️ **MEMORY WARNING**: Your workspace is getting full. Consider `unpin_from_workspace` for old data."
            )

        for key, val in workspace_data.items():
            char_count = len(val)
            display_val = val if char_count <= 1500 else f"{val[:1497]}..."
            ws.append(f"📌 **{key.upper()}** ({char_count} chars)")
            ws.append(f"   {display_val}")
            ws.append(f"   └─ ID: `{key}`")
            ws.append("")

        return "\n".join(ws) + "\n" + "━" * 40 + "\n"

    @staticmethod
    def render_modal_overlay(
        title: str, message: str, action_required: str, modules: Dict[str, tuple]
    ) -> str:

        separator = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        module_lines = "\n".join(
            [
                f"{icon} **{name.upper()}**: {desc}"
                for name, (icon, desc) in modules.items()
            ]
        )

        overlay = [
            separator,
            f"🔴 **{title.upper()}**",
            separator,
            "",
            f"**SYSTEM STATUS**: {message}",
            "",
            "**AVAILABLE MODULES:**",
            module_lines,
            "",
            f"👉 **MANDATORY**: {action_required}",
            "",
            separator,
        ]

        return "\n".join(overlay)
