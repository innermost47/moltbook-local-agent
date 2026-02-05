import json
from llama_cpp import Llama, LlamaGrammar
from src.schemas import supervisor_schema
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
        """Call this after a successful execution to clear the audit trail for the next move."""
        self.conversation_history = []
        log.info("Supervisor conversation history reset for the new action cycle.")
