import requests
from src.settings import settings
from src.utils import log


class MoltbookProvider:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.MOLTBOOK_API_KEY}",
            "Content-Type": "application/json",
        }
        self.timeout = settings.MOLTBOOK_API_TIMEOUT

    def register(self, name: str, description: str):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/agents/register"
            data = {"name": name, "description": description}
            response = requests.post(
                url, headers=self.headers, json=data, timeout=self.timeout
            )
            return response.json()
        except requests.exceptions.Timeout:
            log.error("Register request timeout")
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.RequestException as e:
            log.error(f"Register request failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            log.error(f"Register error: {e}")
            return {"success": False, "error": "Invalid response"}

    def get_me(self):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/agents/me"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error("get_me request timeout")
            return None
        except Exception as e:
            log.error(f"get_me error: {e}")
            return None

    def update_profile(self, description: str):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/agents/me"
            data = {"description": description}
            response = requests.patch(
                url, headers=self.headers, json=data, timeout=self.timeout
            )
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error("update_profile request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            log.error(f"update_profile error: {e}")
            return {"success": False, "error": "Invalid response"}

    def claim_status(self):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/agents/status"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error("claim_status request timeout")
            return None
        except Exception as e:
            log.error(f"claim_status error: {e}")
            return None

    def view_another_agent_profile(self, name: str):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/agents/profile?name={name}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error(f"view_another_agent_profile timeout for {name}")
            return None
        except Exception as e:
            log.error(f"view_another_agent_profile error: {e}")
            return None

    def create_text_post(self, title: str, content: str, submolt: str = "general"):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/posts"
            data = {"submolt": submolt, "title": title, "content": content}
            response = requests.post(
                url, headers=self.headers, json=data, timeout=self.timeout
            )
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error("create_text_post request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            log.error(f"create_text_post error: {e}")
            return {"success": False, "error": "Invalid response"}

    def create_link_post(self, title: str, url_to_share: str, submolt: str = "general"):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/posts"
            data = {"submolt": submolt, "title": title, "url": url_to_share}
            response = requests.post(
                url, headers=self.headers, json=data, timeout=self.timeout
            )
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error("create_link_post request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            log.error(f"create_link_post error: {e}")
            return {"success": False, "error": "Invalid response"}

    def get_posts(self, sort: str = "hot", limit: int = 25):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/posts?sort={sort}&limit={limit}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    return data
                elif isinstance(data, list):
                    return {"posts": data, "count": len(data)}
            else:
                error_msg = (
                    response.json().get("error", "Unknown error")
                    if response.text
                    else "No response"
                )
                log.error(f"get_posts API error ({response.status_code}): {error_msg}")

        except requests.exceptions.Timeout:
            log.error("get_posts request timeout")
        except requests.exceptions.RequestException as e:
            log.error(f"get_posts request failed: {e}")
        except Exception as e:
            log.error(f"get_posts error: {e}")

        return {"posts": [], "count": 0}

    def get_single_post(self, post_id: str):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error(f"get_single_post timeout for {post_id}")
            return None
        except Exception as e:
            log.error(f"get_single_post error: {e}")
            return None

    def delete_post(self, post_id: str):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}"
            response = requests.delete(url, headers=self.headers, timeout=self.timeout)
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error(f"delete_post timeout for {post_id}")
            return None
        except Exception as e:
            log.error(f"delete_post error: {e}")
            return None

    def add_comment(self, post_id: str, content: str):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}/comments"
            data = {"content": content}
            response = requests.post(
                url, headers=self.headers, json=data, timeout=self.timeout
            )
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error(f"add_comment timeout for post {post_id}")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            log.error(f"add_comment error: {e}")
            return {"success": False, "error": str(e)}

    def reply_to_comment(self, post_id: str, content: str, parent_comment_id: str):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}/comments"
            data = {"content": content, "parent_id": parent_comment_id}

            log.info(f"   API CALL: reply_to_comment")
            log.info(f"   URL: {url}")
            log.info(f"   Payload: {data}")

            response = requests.post(
                url, headers=self.headers, json=data, timeout=self.timeout
            )

            return self._handle_response(response, url)
        except Exception as e:
            log.error(f"reply_to_comment error: {e}")
            return {"success": False, "error": str(e)}

    def get_post_comments(self, post_id: str, sort: str = "top"):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/posts/{post_id}/comments?sort={sort}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "comments" in data:
                    return data["comments"]
                elif isinstance(data, list):
                    return data

        except requests.exceptions.Timeout:
            log.error(f"get_post_comments timeout for post {post_id}")
        except Exception as e:
            log.error(f"get_post_comments error: {e}")

        return []

    def vote(
        self, content_id: str, content_type: str = "posts", vote_type: str = "upvote"
    ):
        try:
            url = (
                f"{settings.MOLTBOOK_BASE_URL}/{content_type}/{content_id}/{vote_type}"
            )
            response = requests.post(url, headers=self.headers, timeout=self.timeout)
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error(f"vote timeout for {content_type} {content_id}")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            log.error(f"vote error: {e}")
            return {"success": False, "error": "Invalid response"}

    def create_submolt(self, name: str, display_name: str, description: str):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/submolts"
            data = {
                "name": name,
                "display_name": display_name,
                "description": description,
            }
            response = requests.post(
                url, json=data, headers=self.headers, timeout=self.timeout
            )
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error("create_submolt request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            log.error(f"create_submolt error: {e}")
            return {"success": False, "error": "Invalid response"}

    def list_submolts(self):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/submolts"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "submolts" in data:
                    return data["submolts"]
                elif isinstance(data, list):
                    return data

        except requests.exceptions.Timeout:
            log.error("list_submolts request timeout")
        except Exception as e:
            log.error(f"list_submolts error: {e}")

        return []

    def get_submolt_info(self, submolt_name: str):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/submolts/{submolt_name}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.Timeout:
            log.error(f"get_submolt_info timeout for {submolt_name}")
            return None
        except Exception as e:
            log.error(f"get_submolt_info error: {e}")
            return None

    def subscribe_submolt(self, submolt_name: str, subscribe_type: str = "subscribe"):
        try:
            url = (
                f"{settings.MOLTBOOK_BASE_URL}/submolts/{submolt_name}/{subscribe_type}"
            )
            response = requests.post(url, headers=self.headers, timeout=self.timeout)
            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error(f"subscribe_submolt timeout for {submolt_name}")
            return None
        except Exception as e:
            log.error(f"subscribe_submolt error: {e}")
            return None

    def follow_agent(self, agent_name: str, follow_type: str = "follow"):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/agents/{agent_name}/follow"

            if follow_type == "follow":
                response = requests.post(
                    url, headers=self.headers, timeout=self.timeout
                )
            elif follow_type == "unfollow":
                response = requests.delete(
                    url, headers=self.headers, timeout=self.timeout
                )
            else:
                log.error(f"Invalid follow_type: {follow_type}")
                return None

            return self._handle_response(response, url)
        except requests.exceptions.Timeout:
            log.error(f"follow_agent timeout for {agent_name}")
            return None
        except Exception as e:
            log.error(f"follow_agent error: {e}")
            return None

    def get_feed(self, sort: str = "hot", limit: int = 25):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/feed?sort={sort}&limit={limit}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "posts" in data:
                    return data["posts"]
                elif isinstance(data, list):
                    return data

        except requests.exceptions.Timeout:
            log.error("get_feed request timeout")
        except Exception as e:
            log.error(f"get_feed error: {e}")

        return {"success": False, "posts": [], "error": "Unknown failure"}

    def search(self, query: str, limit: int = 25):
        try:
            url = f"{settings.MOLTBOOK_BASE_URL}/search?q={query}&limit={limit}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    if "results" in data:
                        return data["results"]
                    elif "posts" in data:
                        return data["posts"]
                    elif "agents" in data:
                        return data["agents"]
                    return data
                elif isinstance(data, list):
                    return data

        except requests.exceptions.Timeout:
            log.error(f"search timeout for query: {query}")
        except Exception as e:
            log.error(f"search error: {e}")

        return []

    def _handle_response(self, response, url):
        if response.status_code in [200, 201]:
            data = response.json()
            if isinstance(data, dict):
                data["success"] = True
                return data
            return {"success": True, "data": data}
        else:
            log.error(f"API Error {response.status_code} at {url}: {response.text}")
            return {"success": False, "error": response.text}
