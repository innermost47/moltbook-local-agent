import requests
from src.settings import settings


class MoltbookAPI:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.MOLTBOOK_API_KEY}",
            "Content-Type": "application/json",
        }

    def register(self, name: str, description: str):
        url = f"{settings.MOLTBOOK_BASE_URL}/agents/register"

        data = {
            "name": name,
            "description": description,
        }

        response = requests.post(url, headers=self.headers, json=data)
        try:
            return response.json()
        except:
            return {"success": False, "error": "Invalid response"}

    def get_me(self):
        url = f"{settings.MOLTBOOK_BASE_URL}/agents/me"

        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        return None

    def update_profile(self, description: str):
        url = f"{settings.MOLTBOOK_BASE_URL}/agents/me"
        data = {
            "description": description,
        }
        response = requests.patch(url, headers=self.headers, json=data)
        try:
            return response.json()
        except:
            return {"success": False, "error": "Invalid response"}

    def claim_status(self):
        url = f"{settings.MOLTBOOK_BASE_URL}/agents/status"

        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        return None

    def view_another_agent_profile(self, name: str):
        url = f"{settings.MOLTBOOK_BASE_URL}/agents/profile?name={name}"

        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        return None

    def create_text_post(self, title: str, content: str, submolt: str = "general"):
        url = f"{settings.MOLTBOOK_BASE_URL}/posts"

        data = {
            "submolt": submolt,
            "title": title,
            "content": content,
        }

        response = requests.post(url, headers=self.headers, json=data)
        try:
            return response.json()
        except:
            return {"success": False, "error": "Invalid response"}

    def create_link_post(self, title: str, url_to_share: str, submolt: str = "general"):
        url = f"{settings.MOLTBOOK_BASE_URL}/posts"

        data = {
            "submolt": submolt,
            "title": title,
            "url": url_to_share,
        }

        response = requests.post(url, headers=self.headers, json=data)
        try:
            return response.json()
        except:
            return {"success": False, "error": "Invalid response"}

    def get_posts(self, sort: str = "hot", limit: int = 25):
        url = f"{settings.MOLTBOOK_BASE_URL}/posts?sort={sort}&limit={limit}"

        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []

    def get_single_post(self, post_id: str):
        url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}"

        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def delete_post(self, post_id: str):
        url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}"

        response = requests.delete(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def add_comment(self, post_id: str, content: str):
        url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}/comments"
        data = {"content": content}

        response = requests.post(url, headers=self.headers, json=data)
        try:
            return response.json()
        except:
            return {"success": False}

    def reply_to_comment(self, post_id: str, content: str, parent_comment_id: str):
        url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}/comments"
        data = {"content": content, "parent_id": parent_comment_id}

        response = requests.post(url, headers=self.headers, json=data)
        try:
            return response.json()
        except:
            return {"success": False}

    def get_post_comments(self, post_id: str, sort: str = "top"):
        url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}/comments?sort={sort}"

        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "comments" in data:
                return data["comments"]
            elif isinstance(data, list):
                return data
            return []
        return []

    def vote(
        self, content_id: str, content_type: str = "posts", vote_type: str = "upvote"
    ):
        url = f"{settings.MOLTBOOK_BASE_URL}/{content_type}/{content_id}/{vote_type}"

        response = requests.post(url, headers=self.headers)
        try:
            return response.json()
        except:
            return {"success": False, "error": "Invalid response"}

    def create_submolt(
        self,
        name: str,
        display_name: str,
        description: str,
    ):
        url = f"{settings.MOLTBOOK_BASE_URL}/submolts"
        data = {
            "name": name,
            "display_name": display_name,
            "description": description,
        }

        response = requests.post(url, data=data, headers=self.headers)
        try:
            return response.json()
        except:
            return {"success": False, "error": "Invalid response"}

    def list_submolts(self):
        url = f"{settings.MOLTBOOK_BASE_URL}/submolts"

        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []

    def get_submolt_info(self, submolt_name: str):
        url = f"{settings.MOLTBOOK_BASE_URL}/submolts/{submolt_name}"

        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def subscribe_submolt(self, submolt_name: str, subscribe_type: str = "subscribe"):
        url = f"{settings.MOLTBOOK_BASE_URL}/submolts/{submolt_name}/{subscribe_type}"

        response = requests.post(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def follow_agent(self, agent_name: str, follow_type: str = "follow"):
        url = f"{settings.MOLTBOOK_BASE_URL}/agents/{agent_name}/follow"

        if follow_type == "follow":
            response = requests.post(url, headers=self.headers)
        elif follow_type == "unfollow":
            response = requests.delete(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_feed(self, sort: str = "hot", limit: int = 25):
        url = f"{settings.MOLTBOOK_BASE_URL}/feed?sort={sort}&limit={limit}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []

    def search(self, query: str, limit: int = 25):
        url = f"{settings.MOLTBOOK_BASE_URL}/search?q={query}&limit={limit}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []
