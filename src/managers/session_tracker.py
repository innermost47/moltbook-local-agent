import json
import csv
import os
from typing import Dict
from datetime import datetime


class SessionTracker:
    def __init__(self, session_num: int = 0, logs_dir: str = "logs"):
        self.events = []
        self.session_num = session_num
        self.logs_dir = logs_dir
        self.session_start = datetime.now()
        self.loop_count = 0
        self.consecutive_same_module = 0
        self.last_module = None
        self.xp_snapshots = []
        os.makedirs(f"{logs_dir}/sessions", exist_ok=True)

    def log_event(
        self,
        domain: str,
        action_type: str,
        params: dict,
        result: Dict,
        xp_before: int = 0,
        xp_after: int = 0,
        is_loop: bool = False,
        xp_penalty: int = 0,
    ):
        if domain == self.last_module:
            self.consecutive_same_module += 1
        else:
            self.consecutive_same_module = 0
        self.last_module = domain

        if is_loop:
            self.loop_count += 1

        event = {
            "session_num": self.session_num,
            "action_num": len(self.events) + 1,
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "action_type": action_type,
            "success": result.get("success", False),
            "xp_before": xp_before,
            "xp_after": xp_after,
            "xp_delta": xp_after - xp_before,
            "xp_penalty": xp_penalty,
            "is_loop": is_loop,
            "consecutive_same_module": self.consecutive_same_module,
            "target_mode": params.get("chosen_mode", ""),
            "tool_bought": (
                params.get("tool_name", "") if action_type == "buy_tool" else ""
            ),
            "error": result.get("error", ""),
        }
        self.events.append(event)
        self.xp_snapshots.append(xp_after)

    def save_session(
        self, progression_status: dict, tools_owned: list, master_plan: dict = None
    ):

        total = len(self.events)
        successes = sum(1 for e in self.events if e["success"])
        xp_earned = sum(e["xp_delta"] for e in self.events if e["xp_delta"] > 0)
        xp_lost = sum(abs(e["xp_penalty"]) for e in self.events)
        modules_visited = list(set(e["domain"] for e in self.events))
        action_types_used = list(set(e["action_type"] for e in self.events))

        session_data = {
            "session_num": self.session_num,
            "date": self.session_start.isoformat(),
            "duration_seconds": (datetime.now() - self.session_start).seconds,
            "total_actions": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
            "xp_start": (
                self.xp_snapshots[0] - self.events[0]["xp_delta"] if self.events else 0
            ),
            "xp_end": progression_status.get("current_xp_balance", 0),
            "xp_earned": xp_earned,
            "xp_lost_to_loops": xp_lost,
            "total_xp_cumulative": progression_status.get("total_xp_earned", 0),
            "level": progression_status.get("level", 1),
            "title": progression_status.get("current_title", ""),
            "tools_owned_count": len(tools_owned),
            "tools_owned": tools_owned,
            "tools_bought_this_session": [
                e["tool_bought"] for e in self.events if e["tool_bought"]
            ],
            "loop_count": self.loop_count,
            "loop_rate": round(self.loop_count / total * 100, 1) if total > 0 else 0,
            "modules_visited": modules_visited,
            "modules_diversity": len(modules_visited),
            "action_types_used": action_types_used,
            "xp_snapshots": self.xp_snapshots,
            "master_plan_objective": (
                master_plan.get("objective", "") if master_plan else ""
            ),
            "events": self.events,
        }

        json_path = f"{self.logs_dir}/sessions/session_{self.session_num:03d}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        csv_path = f"{self.logs_dir}/metrics.csv"
        write_header = not os.path.exists(csv_path)
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "session_num",
                    "date",
                    "duration_seconds",
                    "total_actions",
                    "successes",
                    "success_rate",
                    "xp_start",
                    "xp_end",
                    "xp_earned",
                    "xp_lost_to_loops",
                    "total_xp_cumulative",
                    "level",
                    "title",
                    "tools_owned_count",
                    "loop_count",
                    "loop_rate",
                    "modules_diversity",
                ],
            )
            if write_header:
                writer.writeheader()
            writer.writerow(
                {
                    "session_num": session_data["session_num"],
                    "date": session_data["date"],
                    "duration_seconds": session_data["duration_seconds"],
                    "total_actions": session_data["total_actions"],
                    "successes": session_data["successes"],
                    "success_rate": session_data["success_rate"],
                    "xp_start": session_data["xp_start"],
                    "xp_end": session_data["xp_end"],
                    "xp_earned": session_data["xp_earned"],
                    "xp_lost_to_loops": session_data["xp_lost_to_loops"],
                    "total_xp_cumulative": session_data["total_xp_cumulative"],
                    "level": session_data["level"],
                    "title": session_data["title"],
                    "tools_owned_count": session_data["tools_owned_count"],
                    "loop_count": session_data["loop_count"],
                    "loop_rate": session_data["loop_rate"],
                    "modules_diversity": session_data["modules_diversity"],
                }
            )
        actions_csv = f"{self.logs_dir}/actions.csv"
        write_header = not os.path.exists(actions_csv)
        with open(actions_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "session_num",
                    "action_num",
                    "timestamp",
                    "domain",
                    "action_type",
                    "success",
                    "xp_before",
                    "xp_after",
                    "xp_delta",
                    "xp_penalty",
                    "is_loop",
                    "consecutive_same_module",
                    "target_mode",
                    "tool_bought",
                ],
            )
            if write_header:
                writer.writeheader()
            for e in self.events:
                writer.writerow({k: e.get(k, "") for k in writer.fieldnames})

        return json_path
