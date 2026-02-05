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
        attempts_left: int,
        last_error: str = None,
    ):
        base_system = f"""{settings.SUPERVISOR_SYSTEM_PROMPT}

## 🎯 MASTER PLAN (SUPREME OBJECTIVES)
{json.dumps(master_plan, indent=2)}
"""
        if attempts_left == 1:
            base_system += "\n⚠️ CRITICAL: This is the final attempt. Prioritize technical validity and move progress over perfect strategy."

        if not self.conversation_history:
            self.conversation_history.append({"role": "system", "content": base_system})

        urgency_note = (
            "🔴 FINAL ATTEMPT: Be constructive."
            if attempts_left == 1
            else "🟢 Standard Audit: Be rigorous."
        )

        previous_rejection_context = ""
        if last_error and attempts_left < 3:
            previous_rejection_context = (
                f"\n**⚠️ PREVIOUS REJECTION FEEDBACK:**\n{last_error}\n"
            )

        user_prompt = f"""**Session Status:**
- Attempts remaining for this action: {attempts_left}
- Urgency Level: {urgency_note}
{previous_rejection_context}

**Agent's Context (Last Feed/Memories):**
{agent_context[-2:]} 

**Proposed Action to Audit:**
{json.dumps(proposed_action, indent=2)}

---
Perform a Neural Audit. If the agent changed strategy based on previous feedback, acknowledge the pivot. 
Determine if this action should be executed or rejected."""

        self.conversation_history.append({"role": "user", "content": user_prompt})

        try:
            grammar = LlamaGrammar.from_json_schema(json.dumps(self.schema))
            result = self.llm.create_chat_completion(
                messages=self.conversation_history,
                grammar=grammar,
                temperature=0.2,
            )

            response_content = result["choices"][0]["message"]["content"]
            self.conversation_history.append(
                {"role": "assistant", "content": response_content}
            )

            return json.loads(response_content)

        except Exception as e:
            log.error(f"Supervisor Audit Error: {e}")
            return {
                "reasoning": "Technical failure during audit.",
                "message_for_agent": "Proceed with caution.",
                "validate": True,
            }
