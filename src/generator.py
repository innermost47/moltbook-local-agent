import os
import json
from datetime import datetime
from llama_cpp import Llama, LlamaGrammar
from src.settings import settings
from src.utils import log


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
        with open("debug.json", "w", encoding="utf-8") as f:
            json.dump([], f, indent=4, ensure_ascii=False)
        log.success("Model loaded successfully")

    def generate(
        self,
        prompt: str,
        response_format: dict = None,
        save_to_history: bool = True,
        agent_name="Agent",
    ):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        time_aware_prompt = f"""{prompt}

---

**Current Time:** {now}
"""
        messages_for_llm = self.conversation_history + [
            {"role": "user", "content": time_aware_prompt}
        ]

        with open("debug.json", "w", encoding="utf-8") as f:
            json.dump(messages_for_llm, f, indent=4, ensure_ascii=False)

        try:
            grammar = None
            if response_format:
                try:
                    schema_str = json.dumps(response_format)
                    grammar = LlamaGrammar.from_json_schema(schema_str)
                except Exception as e:
                    log.error(f"Grammar creation failed: {e}")

            log.info(f"⚡ LLM is thinking for {agent_name}...")
            waiting_exchange = messages_for_llm + [
                {"role": "assistant", "content": "⏳ Generating response..."}
            ]
            with open("debug.json", "w", encoding="utf-8") as f:
                json.dump(waiting_exchange, f, indent=4, ensure_ascii=False)

            result = self.llm.create_chat_completion(
                messages=messages_for_llm,
                grammar=grammar,
                temperature=0.7,
            )

            assistant_msg = result["choices"][0]["message"]["content"]
            full_exchange = messages_for_llm + [
                {"role": "assistant", "content": assistant_msg}
            ]
            with open("debug.json", "w", encoding="utf-8") as f:
                json.dump(full_exchange, f, indent=4, ensure_ascii=False)

            if save_to_history:
                clean_user_content = f"### 📊 {agent_name.upper()}: Decide next action (Feed context hidden for optimization) [^]"
                self.conversation_history.append(
                    {"role": "user", "content": clean_user_content}
                )
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

        return system_prompt

    def generate_session_summary(self, summary_prompt: str, summary_schema: str):
        log.info(f"⚡ LLM is now generating session summary...")
        result = self.generate(summary_prompt, summary_schema)
        return result["choices"][0]["message"]["content"]

    def generate_simple(self, prompt: str, max_tokens: int = 300) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides concise summaries.",
                },
                {"role": "user", "content": prompt},
            ]
            log.info(f"⚡ LLM is now generating a summary...")
            result = self.llm.create_chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens,
            )

            return result["choices"][0]["message"]["content"]

        except Exception as e:
            log.error(f"Simple generation failed: {e}")
            return f"Error: Unable to generate summary - {str(e)}"

    def trim_history(self):
        if len(self.conversation_history) <= settings.MAX_HISTORY_MESSAGES:
            return

        system_msg = self.conversation_history[0]
        recent_messages = self.conversation_history[
            -(settings.MAX_HISTORY_MESSAGES - 1) :
        ]

        self.conversation_history = [system_msg] + recent_messages
        log.info(f"History trimmed to {len(self.conversation_history)} messages.")
