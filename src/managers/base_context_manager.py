from abc import ABC, abstractmethod


class BaseContextManager(ABC):
    @abstractmethod
    def get_home_snippet(self) -> str:
        pass

    @abstractmethod
    def get_list_view(self, status_msg: str = "") -> str:
        pass

    @abstractmethod
    def get_focus_view(self, item_id: str) -> str:
        pass
