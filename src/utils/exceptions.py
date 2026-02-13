class AgentException(Exception):

    def __init__(self, message: str, suggestion: str, severity: str = "warning"):
        self.message = message
        self.suggestion = suggestion
        self.severity = severity
        super().__init__(self.message)

    def get_visual_feedback(self) -> str:
        """Generate markdown visual feedback for the agent's UI."""
        icon_map = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}

        icon = icon_map.get(self.severity, "⚠️")
        border = "━" * 45

        return f"""
{border}
{icon} **{self.__class__.__name__.replace('Error', '').upper()}**
{border}
**Issue**: {self.message}

💡 **Solution**: {self.suggestion}

⚡ **Impact**: This action consumed 1 energy but produced no valid output.
{border}
"""


class NavigationError(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="warning")


class UnknownActionError(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="critical")

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 **ACTION NOT RECOGNIZED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Error**: {self.message}

💡 **Fix**: {self.suggestion}

📋 **Available Actions**: Check the current mode's action list.

⚠️ Energy wasted. Refer to the UI instructions carefully.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class HallucinationError(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="critical")

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 **INVALID OUTPUT STRUCTURE**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Problem**: {self.message}

💡 **Required**: {self.suggestion}

⚠️ **Penalty**: -1 energy, no progress made.

📌 **Reminder**: Follow the exact schema provided in system instructions.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class LazyContentError(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="critical")

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 **INCOMPLETE CONTENT REJECTED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Violation**: {self.message}

💡 **Required Action**: {self.suggestion}

⛔ **Blocked Terms**: [TODO], [INSERT], [PLACEHOLDER], [TBD]

⚠️ **Consequence**: Energy consumed, zero output produced.

📝 **Standard**: All content must be complete and production-ready.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class FormattingError(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="critical")

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 **FORMATTING VIOLATION**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Parse Error**: {self.message}

💡 **Fix**: {self.suggestion}

📋 **Requirements**:
- Valid JSON structure
- All required fields present
- Correct data types
- No trailing commas or syntax errors

⚠️ Energy wasted due to malformed response.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class AestheticError(AgentException):
    """Raised when content fails quality/style standards."""

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="warning")


class ResourceNotFoundError(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="warning")

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **RESOURCE NOT FOUND**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Error**: {self.message}

💡 **Next Step**: {self.suggestion}

🔍 **Tip**: Refresh the current view to get updated IDs.

⚠️ Energy consumed. Verify resource existence before acting.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class AccessDeniedError(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="critical")

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 **ACCESS DENIED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Security Violation**: {self.message}

💡 **Allowed Action**: {self.suggestion}

🔒 **Reason**: Permission or scope restriction applied.

⚠️ Unauthorized attempts waste energy and may trigger logs.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class DuplicateActionError(AgentException):

    def __init__(self, message: str, suggestion: str, repeat_count: int = 2):
        super().__init__(message=message, suggestion=suggestion, severity="warning")
        self.repeat_count = repeat_count

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **DUPLICATE ACTION DETECTED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Pattern**: {self.message}

🔁 **Repeat Count**: {self.repeat_count}x identical action

💡 **Recommended**: {self.suggestion}

⚡ **Impact**: Wasting energy on redundant operations.

📊 **Optimization**: Vary your actions or move to next phase.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class RateLimitError(AgentException):

    def __init__(self, message: str, suggestion: str, cooldown_seconds: int = 60):
        super().__init__(message=message, suggestion=suggestion, severity="warning")
        self.cooldown_seconds = cooldown_seconds

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **RATE LIMIT EXCEEDED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Throttled**: {self.message}

⏱️ **Cooldown**: {self.cooldown_seconds} seconds

💡 **Alternative**: {self.suggestion}

📌 **Strategy**: Batch operations or switch to different module.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class ActionPointExhausted(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="critical")

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴🔴🔴 **ENERGY DEPLETED** 🔴🔴🔴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Status**: {self.message}

🔋 **Remaining Actions**: 0

💡 **Required**: {self.suggestion}

⛔ **All Actions Blocked** except:
   - session_finish
   - archive_session

⚠️ Session will auto-terminate in next cycle.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class CriticalHealthError(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="critical")

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 **SYSTEM HEALTH CRITICAL**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Internal Error**: {self.message}

💡 **Recovery Action**: {self.suggestion}

⚠️ **Risk**: Continued operation may cause data corruption.

🔧 **Recommendation**: Execute recovery action immediately.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class SessionLimitError(AgentException):

    def __init__(self, message: str, suggestion: str):
        super().__init__(message=message, suggestion=suggestion, severity="critical")


class APICommunicationError(AgentException):

    def __init__(self, message: str, suggestion: str, api_name: str = "Unknown"):
        super().__init__(message=message, suggestion=suggestion, severity="warning")
        self.api_name = api_name

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **API COMMUNICATION FAILURE**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Service**: {self.api_name}

**Error**: {self.message}

💡 **Retry Strategy**: {self.suggestion}

🔄 **Status**: Transient failure - may resolve on retry.

📌 **Alternative**: Try different action or wait briefly.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class LoopDetectionError(AgentException):

    def __init__(self, message: str, suggestion: str, loop_count: int = 3):
        super().__init__(message=message, suggestion=suggestion, severity="critical")
        self.loop_count = loop_count

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 **INFINITE LOOP DETECTED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Pattern**: {self.message}

🔁 **Loop Iterations**: {self.loop_count}x

💡 **Break Loop**: {self.suggestion}

⛔ **BLOCKED**: Repeating this action will auto-fail.

📊 **Analysis**: You are stuck. Change strategy immediately.

⚡ **Energy Wasted**: {self.loop_count} actions consumed with zero progress.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class SystemLogicError(Exception):

    def __init__(self, details: str):
        self.details = details
        super().__init__(self.details)

    def get_visual_feedback(self) -> str:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ **SYSTEM ERROR (Not Your Fault)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Internal Issue**: {self.details}

ℹ️ **Status**: Backend system malfunction.

🔄 **Action**: This has been logged. Try refresh_home or continue.

💡 **Note**: Your energy is NOT consumed for system errors.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


EXCEPTION_PENALTIES = {
    "UnknownActionError": -20,
    "HallucinationError": -15,
    "LazyContentError": -25,
    "FormattingError": -10,
    "DuplicateActionError": -5,
    "LoopDetectionError": -30,
    "AccessDeniedError": -15,
    "ActionPointExhausted": 0,
    "ResourceNotFoundError": -5,
    "RateLimitError": 0,
    "NavigationError": -5,
    "CriticalHealthError": -50,
    "APICommunicationError": 0,
    "SystemLogicError": 0,
}


def get_exception_feedback(exception: Exception) -> dict:
    if isinstance(exception, AgentException):
        return {
            "success": False,
            "severity": exception.severity,
            "error": exception.message,
            "suggestion": exception.suggestion,
            "visual_feedback": exception.get_visual_feedback(),
            "xp_penalty": EXCEPTION_PENALTIES.get(exception.__class__.__name__, -10),
        }
    elif isinstance(exception, SystemLogicError):
        return {
            "success": False,
            "severity": "system",
            "error": exception.details,
            "visual_feedback": exception.get_visual_feedback(),
            "xp_penalty": 0,
        }
    else:
        return {
            "success": False,
            "severity": "critical",
            "error": str(exception),
            "suggestion": "Check system logs or contact administrator.",
            "visual_feedback": f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 **UNEXPECTED ERROR**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{str(exception)}

📋 This error type is not handled. Please report.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
            "xp_penalty": -10,
        }
