from typing import Dict
from datetime import datetime


class SessionTracker:
    def __init__(self):
        self.events = []

    def log_event(self, domain: str, action_type: str, params: dict, result: Dict):
        event = {
            "domain": domain,
            "action": action_type,
            "params": params,
            "result": result,
            "success": result.get("success", False),
            "timestamp": datetime.now().isoformat(),
        }
        self.events.append(event)

    def get_session_report(self) -> str:
        total = len(self.events)
        successes = sum(1 for e in self.events if e.get("success"))
        failures = total - successes

        report = f"""
SESSION REPORT
==============
📊 Stats:
- Total actions: {total}
- Successes: {successes}
- Failures: {failures}
- Success rate: {(successes/total*100) if total > 0 else 0:.1f}%

📋 Actions:
"""
        for event in self.events:
            status = "✅" if event.get("success") else "❌"
            action = event.get("action", "unknown")
            domain = event.get("domain", "unknown")
            report += f"{status} {action} ({domain})\n"

        return report
