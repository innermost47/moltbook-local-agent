class AgentException(Exception):

    def __init__(self, message: str, suggestion: str):
        self.message = message
        self.suggestion = suggestion
        super().__init__(self.message)


class NavigationError(AgentException):
    pass


class UnknownActionError(AgentException):
    pass


class HallucinationError(AgentException):
    pass


class LazyContentError(AgentException):
    pass


class FormattingError(AgentException):
    pass


class AestheticError(AgentException):
    pass


class ResourceNotFoundError(AgentException):
    pass


class AccessDeniedError(AgentException):
    pass


class DuplicateActionError(AgentException):
    pass


class RateLimitError(AgentException):
    pass


class ActionPointExhausted(AgentException):
    pass


class CriticalHealthError(AgentException):
    pass


class SessionLimitError(AgentException):
    pass


class APICommunicationError(AgentException):
    pass


class SystemLogicError(Exception):

    def __init__(self, details: str):
        self.details = details
        super().__init__(self.details)
