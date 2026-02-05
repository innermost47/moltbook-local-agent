import json
from llama_cpp import Llama, LlamaGrammar
from src.schemas import supervisor_schema
from src.settings import settings


class Supervisor:
    def __init__(self, llm_instance: Llama):
        self.llm = llm_instance
        self.schema = supervisor_schema

    def audit(self, agent_context, proposed_action, master_plan, attempts_left: int):
        urgency_note = (
            "🔴 FINAL ATTEMPT: Be constructive and prioritize technical validity."
            if attempts_left == 1
            else "🟢 Standard Audit: Be rigorous."
        )

        prompt = f"""### 📥 INPUT DATA
**Current Master Plan:**
{json.dumps(master_plan, indent=2)}

**Session Status:**
- Attempts remaining for this action: {attempts_left}
- Urgency Level: {urgency_note}

**Agent's Context (Last Feed/Memories):**
{agent_context[-2:]} 

**Proposed Action to Audit:**
{json.dumps(proposed_action, indent=2)}

---
Perform a Neural Audit. Determine if this action should be executed or rejected."""

        messages = [
            {"role": "system", "content": settings.SUPERVISOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        grammar = LlamaGrammar.from_json_schema(json.dumps(self.schema))

        result = self.llm.create_chat_completion(
            messages=messages,
            grammar=grammar,
            temperature=0.2,
        )

        return json.loads(result["choices"][0]["message"]["content"])
