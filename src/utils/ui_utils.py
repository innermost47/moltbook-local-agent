from typing import Optional, Dict
from src.settings import settings


class UIUtils:

    @staticmethod
    def render_navbar(
        current_domain: str, action_count: int, progression_status: Dict = None
    ) -> str:
        terminal_label = "📡 SYSTEM TERMINAL"
        node_status = f"NODE: {current_domain.upper()}"
        width = 70
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

        urgency_message = ""
        energy_percentage = (remaining / max_actions) * 100

        if energy_percentage <= 20:
            urgency_message = (
                "\n🚨 **CRITICAL LOW ENERGY!** Only high-value actions now:\n"
                "   • Publish content (blog/social) to maximize impact\n"
                "   • Complete research and share findings\n"
                "   • NO loops, NO low-value actions, NO exploration\n"
                "   • Every action must create tangible value!"
            )
        elif energy_percentage <= 40:
            urgency_message = (
                "\n⚠️ **LOW ENERGY WARNING** - Prioritize high-impact actions:\n"
                "   • Focus on content creation and community engagement\n"
                "   • Avoid unnecessary navigation and research loops\n"
                "   • Make every action count!"
            )
        elif energy_percentage <= 60:
            urgency_message = (
                "\n💡 **ENERGY MODERATE** - Stay focused on valuable tasks:\n"
                "   • Balance research with content creation\n"
                "   • Avoid repetitive actions"
            )

        prog_display = ""
        if progression_status:
            level = progression_status.get("level", 1)
            title = progression_status.get("current_title", "")
            current_xp_balance = progression_status.get("current_xp_balance", 0)
            xp_progress_in_level = progression_status.get("xp_progress_in_level", 0)
            xp_needed = progression_status.get("xp_needed", 100)
            progress_pct = progression_status.get("progress_percentage", 0)

            xp_bar_width = 30
            xp_percentage = progress_pct / 100
            filled = int(xp_bar_width * xp_percentage)
            empty = xp_bar_width - filled
            xp_bar = "█" * filled + "░" * empty

            prog_display = f"\n⭐ **LVL {level}** {title} | Balance: {current_xp_balance} XP | Progress: [{xp_bar}] {xp_progress_in_level}/{xp_needed} ({progress_pct:.1f}%)"

        return (
            f"{top_line}\n"
            f"{'━' * width}\n"
            f"🌐 {' | '.join(nav_items)}\n"
            f"🔋 {energy_bar} ({remaining}/{max_actions} actions left){prog_display}{urgency_message}\n"
            f"{'━' * width}\n"
        )

    @staticmethod
    def render_feedback(
        success_msg: Optional[str] = None,
        error_msg: Optional[str] = None,
        current_domain: str = "HOME",
        last_action: str = "",
        owned_tools_count: int = 99,
        current_xp_balance: int = 0,
    ) -> str:
        is_on_shop = current_domain.lower() == "shop"
        REPEATABLE_ACTIONS = {
            "comment_post",
            "create_post",
            "write_blog_article",
            "wiki_search",
            "email_send",
        }
        is_early_game = owned_tools_count <= 6
        is_repeatable = last_action in REPEATABLE_ACTIONS
        can_afford_tool = current_xp_balance >= 100
        comments_needed = max(0, -(-(100 - current_xp_balance) // 8))

        feedback = ""

        if is_on_shop:
            shop_hint = ""
        elif can_afford_tool:
            shop_hint = f"🛒 **You have {current_xp_balance} XP - VISIT SHOP NOW!** Use `visit_shop`!"
        elif current_xp_balance > 0:
            shop_hint = f"🛒 **{current_xp_balance}/100 XP** - Need {100 - current_xp_balance} more XP ({comments_needed} comments) then `visit_shop`!"
        else:
            shop_hint = "🛒 **Need tools?** Earn XP then use `visit_shop`!"

        location_reminder = (
            f"\n{'.' * 40}"
            f"\n🧭 **YOU ARE CURRENTLY IN: {current_domain.upper()} MODE**\n"
            f"⛔ **DO NOT call `navigate_to_mode('{current_domain.upper()}')` - you are ALREADY here!**\n"
            f"💡 **Execute an ACTION from the list below**\n"
            + (f"{shop_hint}\n" if shop_hint else "")
        )

        if success_msg:
            feedback += f"\n{'.' * 40}"
            feedback += f"\n✅ **LAST STATUS**: {success_msg}\n"

            if is_repeatable and is_early_game:
                feedback += f"⚠️ Avoid same post/target twice in a row (anti-loop penalty applies).\n"
                if not can_afford_tool:
                    feedback += f"🎯 **Goal**: {comments_needed} more {last_action}(s) → reach 100 XP → `visit_shop`!\n"
                else:
                    feedback += f"✅ **You have {current_xp_balance} XP - GO TO SHOP NOW!** Use `visit_shop`!\n"
            else:
                feedback += (
                    "⚠️ IMPORTANT: DO NOT REPEAT THIS STEP. MOVE IMMEDIATELY TO THE NEXT TASK.\n"
                    "🚨 REPEATING THE SAME ACTION WITH THE SAME PARAMETERS WILL COST YOU XP:\n"
                    "   • 2nd repeat: -10 XP | 3rd repeat: -20 XP | 4th repeat: -30 XP\n"
                    "   • 5th+ repeat: -50 XP, -75 XP, -100 XP (can lose levels!)\n"
                    "   • Choose a DIFFERENT action or navigate to a DIFFERENT module.\n"
                )

        if error_msg:
            feedback += f"\n{'.' * 40}"
            feedback += f"\n❌ **LAST STATUS**: {error_msg}\n"
            feedback += "⚠️ CRITICAL AND MANDATORY: CORRECT THIS ERROR IMMEDIATELY BEFORE PROCEEDING.\n"

        if current_domain.lower() != "home":
            feedback += location_reminder

        return feedback

    @classmethod
    def layout(
        cls,
        content: str,
        current_domain: str = "HOME",
        action_count: int = 0,
        success_msg: str = None,
        error_msg: str = None,
        progression_status: Dict = None,
        notification_section=None,
        modules_status: str = None,
        last_action: str = "",
        owned_tools_count: int = 99,
        current_xp_balance: int = 0,
    ) -> str:

        header = cls.render_navbar(current_domain, action_count, progression_status)
        modules_section = ""
        if modules_status:
            shop_hint = (
                ""
                if current_domain.lower() == "shop"
                else "\n🛒 **Need more capabilities?** Use `visit_shop` to unlock tools with your XP!"
            )
            modules_section = f"""
### 🗺️ MODULES QUICK STATUS
💡 Available actions in other modules (avoid useless navigation):
{modules_status}{shop_hint}
"""

        notifications = cls.render_feedback(
            success_msg,
            error_msg,
            current_domain,
            last_action=last_action,
            owned_tools_count=owned_tools_count,
            current_xp_balance=current_xp_balance,
        )

        return f"{header}{notification_section}{modules_section}{'━' * 70}\n\n{content}\n\n\n{notifications}"

    @staticmethod
    def render_workspace(workspace_data: Dict[str, str]) -> str:
        if not workspace_data:
            return ""

        total_chars = sum(len(v) for v in workspace_data.values())
        is_heavy = total_chars > 2000

        ws = ["### 📋 WORKSPACE (Pinned Data)"]
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

        separator = "━" * 70

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
