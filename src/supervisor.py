import json
from llama_cpp import Llama, LlamaGrammar
from src.schemas import supervisor_schema
from src.settings import settings


class Supervisor:
    def __init__(self, llm_instance: Llama):
        self.llm = llm_instance
        self.schema = supervisor_schema

    def audit(
        self,
        agent_context,
        proposed_action,
        master_plan,
        attempts_left: int,
        last_error: str = None,
    ):
        urgency_note = (
            "🔴 FINAL ATTEMPT: Be constructive and prioritize technical validity."
            if attempts_left == 1
            else "🟢 Standard Audit: Be rigorous."
        )

        previous_rejection_context = ""
        if last_error and attempts_left < 3:
            previous_rejection_context = f"""
**⚠️ PREVIOUS REJECTION FEEDBACK:**
{last_error}
*(Note: If the agent has addressed this feedback or changed strategy to comply, you SHOULD validate it.)*
"""

        prompt = f"""### 📥 INPUT DATA
**Current Master Plan:**
{json.dumps(master_plan, indent=2)}

**Session Status:**
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

        system_content = settings.SUPERVISOR_SYSTEM_PROMPT
        if attempts_left == 1:
            system_content += "\nCRITICAL: Validate if the action is logically sound and technically valid, even if not perfect."

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]

        grammar = LlamaGrammar.from_json_schema(json.dumps(self.schema))

        result = self.llm.create_chat_completion(
            messages=messages,
            grammar=grammar,
            temperature=0.2,
        )

        return json.loads(result["choices"][0]["message"]["content"])
