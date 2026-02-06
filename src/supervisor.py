import json
import re
from llama_cpp import Llama, LlamaGrammar
from src.schemas import supervisor_schema, supervisor_verdict_schema
from src.settings import settings
from src.utils import log


class Supervisor:
    def __init__(self, llm_instance: Llama):
        self.llm = llm_instance
        self.schema = supervisor_schema
        self.conversation_history = []
        log.success("Supervisor initialized with dedicated history")

    def audit(
        self,
        agent_context,
        proposed_action,
        master_plan,
        session_plan: list,
        attempts_left: int,
        last_error: str = None,
    ):
        formatted_session_plan = "\n".join([f"- {task}" for task in session_plan])

        base_system = f"""{settings.SUPERVISOR_SYSTEM_PROMPT}

## 🎯 MASTER PLAN (Long-term Vision)
{json.dumps(master_plan, indent=2)}

## 📝 CURRENT SESSION TO-DO LIST (Immediate Tasks)
{formatted_session_plan}
"""
        if attempts_left == 1:
            base_system += "\n⚠️ CRITICAL: Final attempt. Prioritize technical validity over perfect strategy."

        if not self.conversation_history:
            self.conversation_history.append({"role": "system", "content": base_system})
        else:
            self.conversation_history[0] = {"role": "system", "content": base_system}

        urgency_note = "🔴 FINAL ATTEMPT" if attempts_left == 1 else "🟢 Standard Audit"
        previous_rejection_context = (
            f"\n**⚠️ PREVIOUS REJECTION FEEDBACK:**\n{last_error}\n"
            if last_error
            else ""
        )

        user_prompt = f"""**Session Status:**
- Attempts remaining: {attempts_left}
- Urgency Level: {urgency_note}
{previous_rejection_context}

**Agent's Context (Last Actions/Observations):**
{agent_context[-2:]} 

**Proposed Action to Audit:**
{json.dumps(proposed_action, indent=2)}

---
Perform a Neural Audit. Check if this action completes a task from the To-Do List and stays true to the Master Plan.
If the agent changed strategy based on feedback, validate if the new move is sound."""

        self.conversation_history.append({"role": "user", "content": user_prompt})

        try:
            grammar = LlamaGrammar.from_json_schema(json.dumps(self.schema))
            result = self.llm.create_chat_completion(
                messages=self.conversation_history,
                grammar=grammar,
                temperature=0.1,
            )

            response_content = result["choices"][0]["message"]["content"]
            self.conversation_history.append(
                {"role": "assistant", "content": response_content}
            )

            return json.loads(response_content)

        except Exception as e:
            log.error(f"Supervisor Audit Error: {e}")
            return {
                "reasoning": "Audit bypass due to error.",
                "message_for_agent": "Proceed.",
                "validate": True,
            }

    def reset_history(self):
        self.conversation_history = []
        log.info("Supervisor conversation history reset for the new action cycle.")

    def generate_supervisor_verdict(
        self,
        summary: dict,
        metrics: dict,
        master_plan: dict,
        session_todos: list,
        actions_performed: list,
    ) -> dict:

        formatted_todos = "\n".join(
            [
                f"- [{task.get('priority', 1)}⭐] {task.get('task')}"
                for task in session_todos
            ]
        )

        formatted_actions = "\n".join([f"- {action}" for action in actions_performed])

        verdict_prompt = f"""
## 🧐 END-OF-SESSION PERFORMANCE REVIEW

### 📊 SESSION METRICS
- **Total Actions**: {metrics['total_actions']}
- **Supervisor Rejections**: {metrics['supervisor_rejections']} ({metrics['supervisor_rejections']/metrics['total_actions']*100:.1f}%)
- **Execution Failures**: {metrics['execution_failures']} ({metrics['execution_failures']/metrics['total_actions']*100:.1f}%)
- **Session Score**: {metrics['session_score']:.1f}%

### 🎯 MASTER PLAN (Agent's Strategic Vision)
{json.dumps(master_plan, indent=2)}

### 📋 SESSION TO-DO LIST (What Was Planned)
{formatted_todos}

### ✅ ACTIONS PERFORMED (What Actually Happened)
{formatted_actions}

### 🧠 AGENT'S SELF-SUMMARY
**Reasoning**: {summary.get('reasoning', 'N/A')}
**Learnings**: {summary.get('learnings', 'N/A')}
**Next Session Plan**: {summary.get('next_session_plan', 'N/A')}

---

Based on this complete session context, provide your final verdict:
1. **Overall Assessment** (2-3 sentences, brutally honest)
2. **Main Weakness** (the critical flaw that most impacted performance)
3. **Directive for Next Session** (one concrete, measurable instruction)
4. **Letter Grade** (A+, A, B, C, D, F - calibrated to both metrics AND strategic value)
"""

        try:

            system_prompt = settings.SUPERVISOR_VERDICT_SYSTEM_PROMPT

            grammar = LlamaGrammar.from_json_schema(
                json.dumps(supervisor_verdict_schema)
            )

            result = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": verdict_prompt},
                ],
                grammar=grammar,
                temperature=0.2,
                max_tokens=500,
            )

            content = result["choices"][0]["message"]["content"]
            content = re.sub(r"```json\s*|```\s*", "", content).strip()
            verdict = json.loads(content)

            log.success(f"🧐 Supervisor Grade: {verdict['grade']}")
            return verdict

        except Exception as e:
            log.error(f"Failed to generate supervisor verdict: {e}")
            return {
                "overall_assessment": "Verdict generation failed due to system error.",
                "main_weakness": "System error prevented proper evaluation.",
                "directive_next_session": "Continue operation with caution.",
                "grade": "C",
            }

    def generate_error_guidance(
        self,
        failed_action: dict,
        error_message: str,
        session_todos: list,
        attempts_left: int,
    ) -> str:
        action_type = failed_action.get("action_type", "unknown")
        params = failed_action.get("action_params", {})
        err = error_message.lower()

        if (
            action_type == "update_todo_status"
            and "not found in current session" in err
        ):
            task_names = (
                [t["task"][:100] for t in session_todos] if session_todos else []
            )
            return (
                f"You used '{params.get('todo_task', '?')}' which does not match any task. "
                f"Your valid tasks are:\n"
                + "\n".join([f"  - {t}" for t in task_names])
                + "\nUse a substring that matches one of these descriptions exactly."
            )

        if "no valid ids" in err or "target desync" in err:
            return (
                "The IDs you provided are not in the current feed. "
                "Use 'refresh_feed' to load new posts, or pick IDs from the feed already in your context."
            )

        if "is a comment_id" in err and "reply_to_comment" in err:
            return (
                "You passed a COMMENT_ID where a POST_ID was expected. "
                "Use 'reply_to_comment' with both post_id AND comment_id to reply to a comment."
            )

        if "invalid comment_id" in err:
            return (
                "The comment_id you targeted does not exist in the loaded feed. "
                "Check the COMMENT_IDs listed under each post in your feed context."
            )

        if "protocol violation" in err and (
            "content cannot be empty" in err or "reply content" in err
        ):
            return (
                f"Your '{action_type}' had empty content. "
                "The 'content' field must contain the actual text you want to publish."
            )

        if "schema violation" in err or (
            "invalid category" in err
            and action_type in ["memory_store", "memory_retrieve"]
        ):
            return (
                "You tried to use a memory category that doesn't exist. "
                "Re-read the MEMORY SYSTEM PROTOCOL in your context for the strict list of allowed categories."
            )

        if "already retrieved" in err:
            return (
                "You already retrieved this category recently. The data is in your context. "
                "Move on to a different action."
            )

        if "already attempted" in err or "already published" in err:
            return (
                f"You already used '{action_type}' this session (limit: 1). "
                "Skip this and use your remaining actions on other tasks."
            )

        if "missing mandatory fields" in err and action_type == "write_blog_article":
            return (
                "Your blog article is missing required fields (title and/or content). "
                "The 'content' field must contain the FULL article text, not a placeholder."
            )

        if "security error" in err and "url must be from" in err:
            return (
                "The URL you tried to share is not from your official blog domain. "
                "Use the exact URL returned after 'write_blog_article'."
            )

        if action_type == "share_created_blog_post_url" and ("requires" in err):
            return "You need both 'title' and 'share_link_url' to share a blog post on Moltbook."

        if ("not found" in err) and action_type in [
            "approve_comment_key",
            "reject_comment_key",
            "approve_comment",
            "reject_comment",
        ]:
            return (
                f"The ID you used for '{action_type}' no longer exists or is invalid. "
                "Call 'review_pending_comments' or 'review_comment_key_requests' to refresh the queue first."
            )

        if (
            "not in the whitelist" in err
            or "invalid domain" in err
            or "not allowed" in err
        ):
            return (
                "You tried to access a domain outside your whitelist. "
                "Check the WEB ACCESS section in your context for the list of authorized domains."
            )

        if action_type in ["web_fetch", "web_scrap_for_links"] and (
            "fetch failed" in err or "search failed" in err
        ):
            return (
                "The web request failed (network error, timeout, or empty page). "
                "Try a different URL on the same domain, or switch to another action."
            )

        if action_type == "follow_agent" and "missing" in err:
            return "You must specify 'agent_name' for follow/unfollow actions."

        if "429" in error_message or "rate limit" in err:
            return (
                "Rate limit hit. Wait before retrying this action type, "
                "or pivot to a non-API action (memory, planning, web)."
            )

        if "api error" in err or "server" in err or "http" in err:
            return (
                f"The Moltbook/Blog API returned an error for '{action_type}'. "
                "This may be temporary. Try a different action or retry later."
            )

        if attempts_left > 0:
            return (
                f"'{action_type}' failed: {error_message[:200]}. "
                "Analyze the error, adjust your parameters, and try a DIFFERENT approach."
            )
        else:
            return f"'{action_type}' failed on final attempt. Abandon this action and move on."
