from src.settings import settings


class Metrics:
    def _calculate_session_metrics(self, remaining_actions, actions_performed):
        total_actions = settings.MAX_ACTIONS_PER_SESSION - remaining_actions

        supervisor_rejections = sum(
            1 for action in actions_performed if "[REJECTED]" in action
        )

        execution_failures = sum(
            1 for action in actions_performed if "[FAILED]" in action
        )

        successful_actions = total_actions - supervisor_rejections - execution_failures
        session_score = (
            (successful_actions / total_actions * 100) if total_actions > 0 else 0
        )

        return {
            "total_actions": total_actions,
            "supervisor_rejections": supervisor_rejections,
            "execution_failures": execution_failures,
            "session_score": session_score,
        }

    def _calculate_global_progression(self, app_steps):
        history = app_steps.memory_system.get_session_metrics_history(limit=10)

        if len(history) < 2:
            return {
                "global_score": 50.0,
                "trend": "INITIALIZING",
                "progression_rate": 0.0,
            }

        recent_scores = [s.get("session_score", 50) for s in history[:5]]
        older_scores = [s.get("session_score", 50) for s in history[5:10]]

        recent_avg = sum(recent_scores) / len(recent_scores)
        older_avg = (
            sum(older_scores) / len(older_scores) if older_scores else recent_avg
        )

        progression_rate = recent_avg - older_avg

        if progression_rate > 5:
            trend = "📈 IMPROVING"
        elif progression_rate < -5:
            trend = "📉 DECLINING"
        else:
            trend = "→ STABLE"

        return {
            "global_score": recent_avg,
            "trend": trend,
            "progression_rate": progression_rate,
        }
