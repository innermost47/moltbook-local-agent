import socket
import json
from datetime import datetime
from typing import Dict, Optional
from src.utils import log


class LiveBroadcaster:

    def __init__(self, host: str = "localhost", port: int = 9999):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self._connect()

    def _connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            log.success(f"📡 Connected to Live Viewer at {self.host}:{self.port}")
        except Exception as e:
            log.warning(f"⚠️ Could not connect to Live Viewer: {e}")
            self.connected = False

    def _send_event(self, event: Dict):
        if not self.connected:
            return

        try:
            event_json = json.dumps(event, ensure_ascii=False) + "\n"
            self.socket.sendall(event_json.encode("utf-8"))
        except Exception as e:
            log.warning(f"⚠️ Failed to broadcast event: {e}")
            self.connected = False

    def broadcast_screen(
        self,
        screen_content: str,
        domain: str,
        actions_remaining: int,
        xp_info: Optional[Dict] = None,
    ):
        event = {
            "type": "screen_update",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "screen_content": screen_content,
                "domain": domain.upper(),
                "actions_remaining": actions_remaining,
                "xp_info": xp_info or {},
            },
        }
        self._send_event(event)

    def broadcast_action(
        self,
        action_type: str,
        action_params: Dict,
        reasoning: str = "",
        emotions: str = "",
        self_criticism: str = "",
        next_move_preview: str = "",
        domain: str = "HOME",
    ):
        event = {
            "type": "action_start",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "action_type": action_type,
                "action_params": action_params,
                "reasoning": reasoning,
                "emotions": emotions,
                "self_criticism": self_criticism,
                "next_move_preview": next_move_preview,
                "domain": domain.upper(),
            },
        }
        self._send_event(event)

    def broadcast_result(
        self, action_type: str, success: bool, result_data: str = "", error: str = ""
    ):
        event = {
            "type": "action_result",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "action_type": action_type,
                "success": success,
                "result_data": result_data,
                "error": error,
            },
        }
        self._send_event(event)

    def broadcast_thinking(self, thought: str):
        event = {
            "type": "thinking",
            "timestamp": datetime.now().isoformat(),
            "data": {"thought": thought},
        }
        self._send_event(event)

    def broadcast_session_end(self, summary: Dict):
        event = {
            "type": "session_end",
            "timestamp": datetime.now().isoformat(),
            "data": summary,
        }
        self._send_event(event)

    def close(self):
        if self.socket:
            try:
                self.socket.close()
                log.info("📡 Live Viewer connection closed")
            except:
                pass
