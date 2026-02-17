from abc import ABC
from typing import Dict
from src.utils.exceptions import AgentException, get_exception_feedback


class BaseHandler(ABC):
    def format_success(
        self,
        action_name: str,
        result_data: str,
        anti_loop_hint: str = None,
        xp_gained: int = 0,
        owned_tools_count: int = 99,
    ) -> Dict:

        REPEATABLE_ACTIONS = {
            "comment_post",
            "create_post",
            "write_blog_article",
            "wiki_search",
            "email_send",
        }

        is_early_game = owned_tools_count <= 6
        is_repeatable = action_name in REPEATABLE_ACTIONS

        if anti_loop_hint is None:
            if is_repeatable and is_early_game:
                anti_loop_hint = (
                    f"You can repeat `{action_name}` on DIFFERENT posts/items to earn more XP! "
                    f"Each use earns XP to unlock new tools."
                )
            else:
                anti_loop_hint = (
                    f"Action '{action_name}' just completed. "
                    f"Do not repeat immediately unless you have NEW data."
                )

        xp_message = ""
        if xp_gained > 0:
            xp_message = f"\n\n✨ **+{xp_gained} XP** earned! Keep building your digital presence.\n"

        if is_repeatable and is_early_game:
            repeat_warning = f"💡 **TIP**: You CAN repeat `{action_name}` on different content to earn more XP!"
        else:
            repeat_warning = (
                f"⛔ **DO NOT EXECUTE `{action_name}` AGAIN IMMEDIATELY** ⛔"
            )

        formatted_message = f"""
✅ **ACTION JUST EXECUTED**: `{action_name}`
📦 **RESULT**: {result_data}{xp_message}
🚨 **CRITICAL - READ THIS**: {anti_loop_hint}
{repeat_warning}
"""
        return {
            "success": True,
            "data": formatted_message.strip(),
        }

    def format_error(self, action_name: str, error: Exception) -> Dict:

        if isinstance(error, AgentException):
            feedback = get_exception_feedback(error)

            formatted_message = f"""
❌ **ACTION JUST FAILED**: `{action_name}`

🔴 **ERROR**: {feedback['error']}

💡 **SUGGESTION**: {feedback['suggestion']}

⚠️ **ANTI-LOOP**: This action just failed. Fix the parameters before retrying.
"""

            return {
                "success": False,
                "error": feedback["error"],
                "suggestion": feedback["suggestion"],
                "visual_feedback": formatted_message.strip(),
                "xp_penalty": feedback["xp_penalty"],
                "action_executed": action_name,
            }

        else:
            formatted_message = f"""
❌ **ACTION JUST FAILED**: `{action_name}`

🔴 **ERROR**: {str(error)}

⚠️ **ANTI-LOOP**: This action just encountered an unexpected error. Do not retry immediately.
"""

            return {
                "success": False,
                "error": str(error),
                "visual_feedback": formatted_message.strip(),
                "action_executed": action_name,
            }
