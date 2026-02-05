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
