import json
import re
from llama_cpp import Llama, LlamaGrammar
from pydantic import ValidationError
from src.schemas_pydantic import SupervisorAudit, SupervisorVerdict, LazinessGuidance
from src.settings import settings
from src.utils import log
from src.managers import PromptManager


class Supervisor:
    def __init__(self, llm_instance: Llama):
        self.llm = llm_instance
        self.prompt_manager = PromptManager()
        self.conversation_history = []
        if settings.USE_SUPERVISOR:
            initial_data = []
            log.success("Neural Supervisor activated - Audit system online")
        else:
            initial_data = [
                {
                    "role": "system",
                    "content": "⚠️ Neural Supervisor is disabled for this session. Agent actions will proceed without strategic oversight or validation.",
                }
            ]
            log.warning("Neural Supervisor disabled - Agent running in autonomous mode")
        with open("supervisor_debug.json", "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=4, ensure_ascii=False)

    def audit(
        self,
        agent_context,
        proposed_action,
        master_plan,
        session_plan: list,
        attempts_left: int,
        actions_performed: list,
        post_attempted: bool,
        blog_attempted: bool,
        last_error: str = None,
    ):
        base_system = self.prompt_manager.SUPERVISOR_SYSTEM_PROMPT

        rule_enforcement = ""
        if post_attempted:
            rule_enforcement += (
                "- REJECT any 'create_post' action. One post already published.\n"
            )
        if blog_attempted:
            rule_enforcement += "- REJECT any 'write_blog_article' action. One article already written.\n"

        if rule_enforcement:
            base_system += (
                f"\n\n### 🚫 SESSION CONSTRAINTS (STRICT)\n{rule_enforcement}"
            )

        if attempts_left == 1:
            base_system += "\n\n⚠️ CRITICAL: Final attempt. Prioritize technical validity over perfect strategy."

        if not self.conversation_history:
            self.conversation_history.append({"role": "system", "content": base_system})
        else:
            self.conversation_history[0] = {"role": "system", "content": base_system}

        formatted_session_plan = "\n".join([f"- {task}" for task in session_plan])
        formatted_history = (
            "\n".join([f"✅ {a}" for a in actions_performed])
            if actions_performed
            else "None yet"
        )

        urgency_note = "🔴 FINAL ATTEMPT" if attempts_left == 1 else "🟢 Standard Audit"
        previous_rejection_context = (
            f"\n**⚠️ PREVIOUS REJECTION FEEDBACK:**\n{last_error}\n"
            if last_error
            else ""
        )
        recent_reasoning = "No previous context"
        if agent_context:
            for msg in reversed(agent_context):
                if msg.get("role") == "assistant":
                    try:
                        data = json.loads(msg.get("content", ""))
                        recent_reasoning = data.get(
                            "reasoning", "No specific reasoning found."
                        )
                        break
                    except:
                        continue

            if attempts_left == 3:
                memory_context = "- **Previous Action Intent:** None (Initial step)"
            else:
                memory_context = f'- **FAILED PREVIOUS INTENT:** "{recent_reasoning}"'

            user_prompt = self.prompt_manager.get_audit_prompt(
                urgency_note=urgency_note,
                memory_context=memory_context,
                attempts_left=attempts_left,
                previous_rejection_context=previous_rejection_context,
                formatted_history=formatted_history,
                formatted_session_plan=formatted_session_plan,
                proposed_action=proposed_action,
                master_plan=master_plan,
            )

        messages_for_audit = self.conversation_history + [
            {"role": "user", "content": user_prompt}
        ]

        try:
            log.info(f"⚡ LLM is now generating an audit for supervisor...")
            debug_data = messages_for_audit.copy()
            waiting_debug = debug_data + [
                {"role": "assistant", "content": "🔍 Analyzing agent proposal..."}
            ]
            with open("supervisor_debug.json", "w", encoding="utf-8") as f:
                json.dump(waiting_debug, f, indent=4, ensure_ascii=False)

            grammar = LlamaGrammar.from_json_schema(
                json.dumps(SupervisorAudit.model_json_schema())
            )
            result = self.llm.create_chat_completion(
                messages=messages_for_audit,
                grammar=grammar,
                temperature=0.1,
            )
            response_content = result["choices"][0]["message"]["content"]
            try:
                audit_verdict = SupervisorAudit.model_validate_json(response_content)
                log.success(f"✅ Supervisor audit validated (Pydantic)")
                audit_dict = audit_verdict.model_dump()
                log.info(f"💬 SUPERVISOR FEEDBACK: {audit_dict['message_for_agent']}")

            except ValidationError as e:
                log.error(f"❌ Supervisor audit validation failed:")
                for error in e.errors():
                    log.error(f"  - {error['loc']}: {error['msg']}")

                audit_dict = json.loads(response_content)

            clean_summary = f"Audit for action... Verdict: {audit_dict.get('is_valid')}"
            self.conversation_history.append({"role": "user", "content": clean_summary})
            self.conversation_history.append(
                {"role": "assistant", "content": response_content}
            )
            debug_data.append({"role": "assistant", "content": response_content})

            with open("supervisor_debug.json", "w", encoding="utf-8") as f:
                json.dump(debug_data, f, indent=4, ensure_ascii=False)

            return audit_dict

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

        verdict_prompt = self.prompt_manager.get_verdict_prompt(
            metrics=metrics,
            master_plan=master_plan,
            formatted_todos=formatted_todos,
            formatted_actions=formatted_actions,
            summary=summary,
        )

        try:

            system_prompt = self.prompt_manager.SUPERVISOR_VERDICT_SYSTEM_PROMPT

            grammar = LlamaGrammar.from_json_schema(
                json.dumps(SupervisorVerdict.model_json_schema())
            )
            log.info(f"⚡ LLM is now generating an session verdict for supervisor...")
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

            try:
                verdict_obj = SupervisorVerdict.model_validate_json(content)
                verdict = verdict_obj.model_dump()
                log.success(f"🧐 Supervisor Grade: {verdict['grade']}")
            except ValidationError as e:
                log.error(f"❌ Verdict validation failed: {e}")
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

        guidance = None

        if (
            action_type == "update_todo_status"
            and "not found in current session" in err
        ):
            task_names = (
                [t["task"][:100] for t in session_todos] if session_todos else []
            )
            guidance = (
                f"You used '{params.get('todo_task', '?')}' which does not match any task. "
                f"Your valid tasks are:\n"
                + "\n".join([f"  - {t}" for t in task_names])
                + "\nUse a substring that matches one of these descriptions exactly."
            )

        elif "no valid ids" in err or "target desync" in err:
            guidance = (
                "The IDs you provided are not in the current feed. "
                "Use 'refresh_feed' to load new posts, or pick IDs from the feed already in your context."
            )

        elif "is a comment_id" in err and "reply_to_comment" in err:
            guidance = (
                "You passed a COMMENT_ID where a POST_ID was expected. "
                "Use 'reply_to_comment' with both post_id AND comment_id to reply to a comment."
            )

        elif "invalid comment_id" in err:
            guidance = (
                "The comment_id you targeted does not exist in the loaded feed. "
                "Check the COMMENT_IDs listed under each post in your feed context."
            )

        elif "protocol violation" in err and (
            "content cannot be empty" in err or "reply content" in err
        ):
            guidance = (
                f"Your '{action_type}' had empty content. "
                "The 'content' field must contain the actual text you want to publish."
            )

        elif "schema violation" in err or (
            "invalid category" in err
            and action_type in ["memory_store", "memory_retrieve"]
        ):
            guidance = (
                "You tried to use a memory category that doesn't exist. "
                "Re-read the MEMORY SYSTEM PROTOCOL in your context for the strict list of allowed categories."
            )

        elif "already retrieved" in err:
            guidance = (
                "You already retrieved this category recently. The data is in your context. "
                "Move on to a different action."
            )

        elif "already attempted" in err or "already published" in err:
            guidance = (
                f"You already used '{action_type}' this session (limit: 1). "
                "Skip this and use your remaining actions on other tasks."
            )

        elif "missing mandatory fields" in err and action_type == "write_blog_article":
            guidance = (
                "Your blog article is missing required fields (title and/or content). "
                "The 'content' field must contain the FULL article text, not a placeholder."
            )

        elif "security error" in err and "url must be from" in err:
            guidance = (
                "The URL you tried to share is not from your official blog domain. "
                "Use the exact URL returned after 'write_blog_article'."
            )

        elif action_type == "share_created_blog_post_url" and ("requires" in err):
            guidance = "You need both 'title' and 'share_link_url' to share a blog post on Moltbook."

        elif ("not found" in err) and action_type in [
            "approve_comment_key",
            "reject_comment_key",
            "approve_comment",
            "reject_comment",
        ]:
            guidance = (
                f"The ID you used for '{action_type}' no longer exists or is invalid. "
                "Call 'review_pending_comments' or 'review_comment_key_requests' to refresh the queue first."
            )

        elif (
            "not in the whitelist" in err
            or "invalid domain" in err
            or "not allowed" in err
        ):
            guidance = (
                "You tried to access a domain outside your whitelist. "
                "Check the WEB ACCESS section in your context for the list of authorized domains."
            )

        elif action_type in ["web_fetch", "web_scrap_for_links"] and (
            "fetch failed" in err or "search failed" in err
        ):
            guidance = (
                "The web request failed (network error, timeout, or empty page). "
                "Try a different URL on the same domain, or switch to another action."
            )

        elif action_type == "follow_agent" and "missing" in err:
            guidance = "You must specify 'agent_name' for follow/unfollow actions."

        elif "429" in error_message or "rate limit" in err:
            guidance = (
                "Rate limit hit. Wait before retrying this action type, "
                "or pivot to a non-API action (memory, planning, web)."
            )

        elif "api error" in err or "server" in err or "http" in err:
            guidance = (
                f"The Moltbook/Blog API returned an error for '{action_type}'. "
                "This may be temporary. Try a different action or retry later."
            )

        elif attempts_left > 0:
            guidance = (
                f"'{action_type}' failed: {error_message[:200]}. "
                "Analyze the error, adjust your parameters, and try a DIFFERENT approach."
            )
        else:
            guidance = f"'{action_type}' failed on final attempt. Abandon this action and move on."

        error_context_prompt = f"""
## ❌ ERROR GUIDANCE REQUEST

**Failed Action:** {action_type}
**Error Message:** {error_message}
**Attempts Left:** {attempts_left}

**Action Params:**
{json.dumps(params, indent=2)}

**Session TO-DO List:**
{chr(10).join([f"- {t['task']}" for t in session_todos]) if session_todos else "None"}
"""
        messages = [
            {"role": "user", "content": error_context_prompt},
            {"role": "assistant", "content": guidance},
        ]

        try:
            try:
                with open("supervisor_debug.json", "r", encoding="utf-8") as f:
                    debug_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                debug_data = []

            debug_data.extend(messages)

            with open("supervisor_debug.json", "w", encoding="utf-8") as f:
                json.dump(debug_data, f, indent=4, ensure_ascii=False)

            log.info(f"📝 Error guidance saved to debug file")

        except Exception as e:
            log.error(f"Failed to save error guidance debug: {e}")

        return guidance

    def generate_laziness_guidance(
        self,
        lazy_action: dict,
        offending_pattern: str,
        session_todos: list,
        attempts_left: int,
    ) -> str:
        action_type = lazy_action.get("action_type", "unknown")

        formatted_todos = "\n".join(
            [
                f"- [{task.get('priority', 1)}⭐] {task.get('task')}"
                for task in session_todos
            ]
        )

        laziness_prompt = self.prompt_manager.get_lazyness_sys_prompt(
            action_type=action_type,
            offending_pattern=offending_pattern,
            lazy_action=lazy_action,
            formatted_todos=formatted_todos,
            attempts_left=attempts_left,
        )

        try:
            try:
                with open("supervisor_debug.json", "r", encoding="utf-8") as f:
                    debug_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                debug_data = []

            messages = [
                {
                    "role": "system",
                    "content": "You are the Neural Supervisor providing actionable feedback to correct lazy behavior.",
                },
                {"role": "user", "content": laziness_prompt},
            ]

            grammar = LlamaGrammar.from_json_schema(
                json.dumps(LazinessGuidance.model_json_schema())
            )
            log.info(f"⚡ LLM is now generating laziness guidance...")

            debug_data.extend(messages)
            debug_data.append(
                {
                    "role": "assistant",
                    "content": "⚠️ Detecting laziness patterns and drafting corrections...",
                }
            )

            with open("supervisor_debug.json", "w", encoding="utf-8") as f:
                json.dump(debug_data, f, indent=4, ensure_ascii=False)

            result = self.llm.create_chat_completion(
                messages=messages,
                grammar=grammar,
                temperature=0.3,
                max_tokens=200,
            )
            content = result["choices"][0]["message"]["content"]
            try:
                guidance_obj = LazinessGuidance.model_validate_json(content)
                guidance = (
                    f"**Problem:** {guidance_obj.problem_diagnosis}\n"
                    f"**Required:** {guidance_obj.required_content}\n"
                    f"**Action:** {guidance_obj.actionable_instruction}"
                )
            except ValidationError as e:
                log.error(f"❌ Laziness validation failed: {e}")
                guidance_json = json.loads(content)
                guidance = (
                    f"**Problem:** {guidance_json['problem_diagnosis']}\n"
                    f"**Required:** {guidance_json['required_content']}\n"
                    f"**Action:** {guidance_json['actionable_instruction']}"
                )

            debug_data[-1] = {"role": "assistant", "content": content}

            with open("supervisor_debug.json", "w", encoding="utf-8") as f:
                json.dump(debug_data, f, indent=4, ensure_ascii=False)
            log.info(f"🧐 Laziness guidance saved to debug file")

            return guidance

        except Exception as e:
            log.error(f"Failed to generate laziness guidance: {e}")

            try:
                with open("supervisor_debug.json", "r", encoding="utf-8") as f:
                    debug_data = json.load(f)
            except:
                debug_data = []

            debug_data.extend(
                [
                    {
                        "role": "system",
                        "content": "Laziness guidance generation failed",
                    },
                    {"role": "user", "content": laziness_prompt},
                    {"role": "assistant", "content": f"ERROR: {str(e)}"},
                ]
            )

            with open("supervisor_debug.json", "w", encoding="utf-8") as f:
                json.dump(debug_data, f, indent=4, ensure_ascii=False)

            return (
                f"Forbidden pattern '{offending_pattern}' detected. "
                f"Replace ALL placeholders with real, specific content related to your session goals."
            )
