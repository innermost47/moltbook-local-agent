from abc import ABC, abstractmethod


class BaseContextManager(ABC):
    @abstractmethod
    def get_home_snippet(self) -> str:
        pass

    @abstractmethod
    def get_list_view(self, status_msg: str = "", workspace_pins=None) -> str:
        pass

    @abstractmethod
    def get_focus_view(self, item_id: str) -> str:
        pass

    def _extract_title_from_url(self, url: str) -> str:
        try:
            if "slug=" in url:
                slug = url.split("slug=")[-1].split("&")[0]
                return slug.replace("-", " ").title()
        except Exception:
            pass
        return "New Blog Article"
