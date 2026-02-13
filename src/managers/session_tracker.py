from datetime import datetime
from src.utils import log


class SessionTracker:
    def __init__(self):
        self.xp = 0
        self.level = 1
        self.events = []
        self.xp_history = []

    def apply_penalty(self, exception_name: str, xp_penalty: int):
        if xp_penalty == 0:
            return

        self.xp += xp_penalty

        log.warning(f"⚠️ XP Penalty: {xp_penalty} ({exception_name})")

        self.xp_history.append(
            {
                "type": "penalty",
                "exception": exception_name,
                "xp": xp_penalty,
                "timestamp": datetime.now().isoformat(),
            }
        )

        self._check_level_change()

    def _check_level_change(self):
        xp_per_level = 100
        new_level = max(1, (self.xp // xp_per_level) + 1)

        if new_level != self.level:
            old_level = self.level
            self.level = new_level
            log.success(f"🎉 Level {old_level} → {new_level}!")

    def log_event(self, domain: str, action_type: str, result: dict):
        event = {
            "domain": domain,
            "action": action_type,
            "success": result.get("success", False),
            "timestamp": datetime.now().isoformat(),
        }

        self.events.append(event)

        if result.get("success"):
            xp_gain = 10
            self.xp += xp_gain
            self.xp_history.append(
                {
                    "type": "gain",
                    "action": action_type,
                    "xp": xp_gain,
                    "timestamp": event["timestamp"],
                }
            )
            self._check_level_change()

    def get_session_report(self) -> str:
        total = len(self.events)
        successes = sum(1 for e in self.events if e["success"])
        failures = total - successes

        report = f"""
SESSION REPORT
==============

📊 Stats:
- Total actions: {total}
- Successes: {successes}
- Failures: {failures}
- Success rate: {(successes/total*100) if total > 0 else 0:.1f}%

🎮 Gamification:
- XP: {self.xp}
- Level: {self.level}

📋 Actions:
"""
        for event in self.events:
            status = "✅" if event["success"] else "❌"
            report += f"{status} {event['action']} ({event['domain']})\n"

        return report
