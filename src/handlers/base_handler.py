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
    ) -> Dict:
        if anti_loop_hint is None:
            anti_loop_hint = f"Action '{action_name}' just completed successfully. Do not repeat immediately unless you have NEW data."

        xp_message = ""
        if xp_gained > 0:
            xp_message = f"\n\n✨ **+{xp_gained} XP** earned! Keep building your digital presence.\n"

        formatted_message = f"""
✅ **ACTION JUST EXECUTED**: `{action_name}`
📦 **RESULT**: {result_data}{xp_message}
🚨 **CRITICAL - READ THIS**: {anti_loop_hint}

⛔ **DO NOT EXECUTE `{action_name}` AGAIN** ⛔
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
