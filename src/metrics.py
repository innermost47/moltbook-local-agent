class Metrics:
    def _calculate_session_metrics(
        self, actions_performed, actions_failed, actions_rejected, actions_aborted
    ):
        success_count = len(actions_performed)
        failed_count = len(actions_failed)
        rejected_count = len(actions_rejected)
        aborted_count = len(actions_aborted)

        total_actions = success_count + rejected_count + failed_count + aborted_count

        session_score = (
            (success_count / total_actions * 100) if total_actions > 0 else 0
        )

        return {
            "total_actions": total_actions,
            "supervisor_rejections": rejected_count,
            "execution_failures": failed_count,
            "aborted_tasks": aborted_count,
            "session_score": round(session_score, 2),
            "success_count": success_count,
        }

    def _calculate_global_progression(self, app_steps):
        history = app_steps.memory_system.get_session_metrics_history(limit=10)

        if not history or len(history) < 2:
            return {
                "global_score": (
                    history[0].get("session_score", 50.0) if history else 50.0
                ),
                "trend": "INITIALIZING 🆕",
                "progression_rate": 0.0,
            }

        recent_data = history[:5]
        older_data = history[5:10]

        recent_avg = sum(s.get("session_score", 0) for s in recent_data) / len(
            recent_data
        )

        if older_data:
            older_avg = sum(s.get("session_score", 0) for s in older_data) / len(
                older_data
            )
            progression_rate = recent_avg - older_avg
        else:
            previous_score = history[1].get("session_score", recent_avg)
            progression_rate = recent_avg - previous_score

        if progression_rate > 3:
            trend = "📈 IMPROVING"
        elif progression_rate < -3:
            trend = "📉 DECLINING"
        else:
            trend = "→ STABLE"

        return {
            "global_score": round(recent_avg, 2),
            "trend": trend,
            "progression_rate": round(progression_rate, 2),
        }
