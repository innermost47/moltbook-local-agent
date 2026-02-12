from datetime import datetime
from typing import List, Dict, Any


class SessionTracker:
    def __init__(self):
        self.start_time = datetime.now()
        self.history: List[Dict[str, Any]] = []
        self.xp = 0

    def log_event(self, domain: str, action_type: str, result: Dict[str, Any]):
        success = result.get("success", False)
        timestamp = datetime.now().strftime("%H:%M:%S")

        gain = 10 if success else -5
        self.xp += gain

        entry = {
            "time": timestamp,
            "domain": domain,
            "action": action_type,
            "status": "✅" if success else "❌",
            "xp_gain": gain,
            "details": result.get("data", "") if success else result.get("error", ""),
        }
        self.history.append(entry)

    def get_session_report(self) -> str:
        duration = datetime.now() - self.start_time
        success_count = sum(1 for e in self.history if e["status"] == "✅")

        report = f"📊 SESSION REPORT\n"
        report += f"⏱ Duration: {str(duration).split('.')[0]}\n"
        report += f"📈 Success Rate: {success_count}/{len(self.history)}\n"
        report += f"🎮 XP Earned: {self.xp}\n\n"
        report += "LOGS:\n"
        for e in self.history:
            report += f"[{e['time']}] {e['status']} {e['action']} in {e['domain']} ({e['xp_gain']} XP)\n"
        return report
