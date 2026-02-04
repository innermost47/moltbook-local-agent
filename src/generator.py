import os
import json
from llama_cpp import Llama, LlamaGrammar
from src.settings import settings
from src.utils import log
from src.memory import Memory


class Generator:
    def __init__(self):
        log.info(f"Loading model: {settings.LLAMA_CPP_MODEL}")
        self.llm = Llama(
            model_path=settings.LLAMA_CPP_MODEL,
            n_ctx=settings.LLAMA_CPP_MODEL_CTX_SIZE,
            n_gpu_layers=-1,
            n_threads=settings.LLAMA_CPP_MODEL_THREADS,
            verbose=False,
            chat_format="chatml",
        )
        self.conversation_history = []
        log.success("Model loaded successfully")

    def generate(self, prompt: str, response_format: dict = None):

        self.conversation_history.append({"role": "user", "content": prompt})

        messages = [
            {
                "role": "system",
                "content": self.get_main_system_prompt(),
            }
        ] + self.conversation_history

        try:
            grammar = None
            if response_format:
                try:
                    schema_str = json.dumps(response_format)
                    grammar = LlamaGrammar.from_json_schema(schema_str)
                except Exception as e:
                    log.error(f"Grammar creation failed: {e}")
            result = self.llm.create_chat_completion(
                messages=messages,
                grammar=grammar,
                temperature=0.7,
            )

            assistant_msg = result["choices"][0]["message"]["content"]
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_msg}
            )

            return result

        except Exception as e:
            log.error(f"LLM generation failed: {e}")
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"reasoning": "Error during generation", "action_type": "check_feed", "action_params": {"sort": "hot", "limit": 5}}'
                        }
                    }
                ]
            }

    def get_main_system_prompt(self):
        system_prompt = ""

        if os.path.exists(settings.MAIN_AGENT_FILE_PATH):
            with open(settings.MAIN_AGENT_FILE_PATH, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        elif os.path.exists(settings.BASE_AGENT_FILE_PATH):
            with open(settings.BASE_AGENT_FILE_PATH, "r", encoding="utf-8") as f:
                system_prompt = f.read()

        memory = Memory()
        last_session = memory.get_last_session()

        if last_session:
            memory_injection = f"""

## PREVIOUS SESSION MEMORY

**Date:** {last_session['timestamp']}

**Actions I performed:**
{chr(10).join(f"- {action}" for action in last_session['actions_performed'])}

**What I learned:**
{last_session['learnings']}

**My plan for THIS session:**
{last_session['next_session_plan']}
"""
            system_prompt += memory_injection

        return system_prompt

    def generate_session_summary(self, actions_performed: list):

        summary_schema = {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Your thought process about this session",
                },
                "learnings": {
                    "type": "string",
                    "description": "What you learned from interactions and feedback",
                },
                "next_session_plan": {
                    "type": "string",
                    "description": "What you plan to do in the next session",
                },
            },
            "required": ["reasoning", "learnings", "next_session_plan"],
        }

        summary_prompt = f"""
Session completed. Here's what happened:

Actions performed: {len(actions_performed)}
{chr(10).join(f"- {action}" for action in actions_performed)}

Reflect on this session and create a summary with:
1. Your reasoning about what worked/didn't work
2. Key learnings from user interactions
3. Your strategic plan for the next session

Respond in JSON format.
"""
        grammar = None
        try:
            schema_str = json.dumps(summary_schema)
            grammar = LlamaGrammar.from_json_schema(schema_str)
        except Exception as e:
            log.error(f"Grammar creation failed: {e}")

        result = self.generate(summary_prompt, grammar=grammar)
        return result["choices"][0]["message"]["content"]

    def clear_conversation(self):
        self.conversation_history = []

    def generate_simple(self, prompt: str, max_tokens: int = 300) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides concise summaries.",
                },
                {"role": "user", "content": prompt},
            ]

            result = self.llm.create_chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens,
            )

            return result["choices"][0]["message"]["content"]

        except Exception as e:
            log.error(f"Simple generation failed: {e}")
            return f"Error: Unable to generate summary - {str(e)}"
