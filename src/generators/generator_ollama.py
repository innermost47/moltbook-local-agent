import os
from src.settings import settings
from datetime import datetime
from pydantic import ValidationError
import ollama
from src.utils import log


class OllamaGenerator:
    def __init__(self, model="qwen2.5:7b"):
        self.model = model
        self.conversation_history = []

        try:
            ollama.list()
            log.success(f"Ollama connected - using model: {model}")
        except Exception as e:
            log.error(f"Ollama connection failed: {e}")
            raise

    def generate(
        self,
        prompt: str,
        pydantic_model=None,
        save_to_history: bool = True,
        agent_name="Agent",
        heavy_context: str = "",
        temperature: float = None,
        **kwargs,
    ):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        full_llm_payload = (
            f"{heavy_context}\n\n{prompt}\n\n---\n**Current Time:** {now}"
        )

        messages_for_llm = self.conversation_history + [
            {"role": "user", "content": full_llm_payload}
        ]

        if temperature is None:
            temperature = 0.2 if pydantic_model else 0.7

        try:
            log.info(f"⚡ Ollama is thinking for {agent_name}...")

            if pydantic_model:
                json_schema = pydantic_model.model_json_schema()

                response = ollama.chat(
                    model=self.model,
                    messages=messages_for_llm,
                    format=json_schema,
                    options={
                        "temperature": temperature,
                        "num_ctx": 8192,
                    },
                )

                assistant_msg = response["message"]["content"]

                try:
                    clean_json = assistant_msg.strip()
                    validated = pydantic_model.model_validate_json(clean_json)
                    assistant_msg = validated.model_dump_json(indent=2)
                    log.success(
                        f"✅ Pydantic validation passed ({pydantic_model.__name__})"
                    )
                except ValidationError as e:
                    log.error(f"❌ Pydantic validation failed:")
                    for error in e.errors():
                        log.error(f"  - {error['loc']}: {error['msg']}")
                    log.warning("⚠️ Using unvalidated output")

            else:
                response = ollama.chat(
                    model=self.model,
                    messages=messages_for_llm,
                    options={
                        "temperature": temperature,
                        "num_ctx": 8192,
                    },
                )
                assistant_msg = response["message"]["content"]

            if save_to_history:
                self.conversation_history.append(
                    {"role": "user", "content": f"{prompt}\n\n**Time:** {now}"}
                )
                self.conversation_history.append(
                    {"role": "assistant", "content": assistant_msg}
                )
            return {"choices": [{"message": {"content": assistant_msg}}]}

        except Exception as e:
            log.error(f"Ollama generation failed: {e}")
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"reasoning": "Error during generation", "action_type": "refresh_feed", "action_params": {"sort": "top"}}'
                        }
                    }
                ]
            }

    def generate_session_summary(self, summary_prompt: str, pydantic_model=None):
        log.info(f"⚡ Ollama is generating session summary...")
        result = self.generate(summary_prompt, pydantic_model=pydantic_model)
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

            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": 0.3,
                    "num_predict": max_tokens,
                },
            )

            return response["message"]["content"]

        except Exception as e:
            log.error(f"Simple generation failed: {e}")
            return f"Error: Unable to generate summary - {str(e)}"

    def trim_history(self, max_messages: int = 10):
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]
            log.info(f"History trimmed to {len(self.conversation_history)} messages.")

    def get_main_system_prompt(self):
        system_prompt = ""
        if os.path.exists(settings.MAIN_AGENT_FILE_PATH):
            with open(settings.MAIN_AGENT_FILE_PATH, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        elif os.path.exists(settings.BASE_AGENT_FILE_PATH):
            with open(settings.BASE_AGENT_FILE_PATH, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        return system_prompt
