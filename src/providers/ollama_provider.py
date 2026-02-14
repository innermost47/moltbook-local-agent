import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Type, Any
from pydantic import BaseModel, ValidationError
from ollama import Client
import tiktoken
from src.settings import settings
from src.utils import log
from src.utils.exceptions import FormattingError, HallucinationError
from argparse import Namespace


class OllamaProvider:
    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model

        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
            log.warning("⚠️ tiktoken not available, falling back to Ollama count")

        if settings.USE_OLLAMA_PROXY:
            proxy_url = getattr(settings, "OLLAMA_PROXY_URL", "http://localhost:8000")
            api_key = settings.OLLAMA_PROXY_API_KEY
            self.client = Client(host=proxy_url, headers={"X-API-Key": api_key})
            log.info(f"🌐 Ollama Generator PROXY mode enabled to {proxy_url}")
        else:
            self.client = Client(host="http://localhost:11434")
            log.info("🏠 LOCAL Mode enabled (Direct Ollama)")

    def get_next_action(
        self,
        current_context: str,
        actions_left: int,
        schema: Type[BaseModel],
        conversation_history: List[Dict],
        agent_name: str,
        debug_filename="debug.json",
    ) -> tuple[Namespace, List[Dict]]:

        prompt = f"Analyze the dashboard and decide your next move. Actions left: {actions_left}/{settings.MAX_ACTIONS_PER_SESSION}"

        response, updated_history = self.generate(
            prompt=prompt,
            heavy_context=current_context,
            pydantic_model=schema,
            agent_name=agent_name,
            conversation_history=conversation_history,
            debug_filename=debug_filename,
            command_label="🚀 **USER COMMAND**",
        )

        content = response.get("message", {}).get("content", "{}")

        try:
            raw_data = self._robust_json_parser(content)
            if (
                not raw_data
                or raw_data.get("action_type") == "refresh_home"
                and "reasoning" not in raw_data
            ):
                raise FormattingError(
                    message="The LLM returned an empty or invalid JSON structure.",
                    suggestion="Please respect the JSON schema provided in the system instructions.",
                )
            action_payload = raw_data.get("action") or raw_data.get("selection")

            if not action_payload:
                raise HallucinationError(
                    message="Action payload missing from the response root.",
                    suggestion=f"Ensure your response is wrapped in a key matching the {schema.__name__} requirements.",
                )

            flattened = {
                "reasoning": raw_data.get("reasoning", ""),
                "self_criticism": raw_data.get("self_criticism", ""),
                "emotions": raw_data.get("emotions", ""),
                "next_move_preview": raw_data.get("next_move_preview", ""),
            }

            if "chosen_mode" in action_payload:
                flattened["action_type"] = "navigate_to_mode"
                flattened["action_params"] = {
                    "mode": action_payload.get("chosen_mode"),
                    "expected_actions": action_payload.get("expected_actions_count"),
                }
            else:
                flattened["action_type"] = action_payload.get("action_type")
                flattened["action_params"] = action_payload.get("action_params", {})

            if not flattened.get("action_type"):
                raise HallucinationError(
                    message="Parsed action has no 'action_type'.",
                    suggestion="Check the Literal value of 'action_type' in your Pydantic model.",
                )

            return Namespace(**flattened), updated_history  # ✅

        except (FormattingError, HallucinationError) as e:
            log.warning(f"⚠️ {type(e).__name__}: {e.message}")
            return (
                Namespace(
                    action_type="refresh_home",
                    action_params={"error_suggestion": e.suggestion},
                    reasoning=f"Error: {e.message}",
                ),
                updated_history,
            )
        except Exception as e:
            log.error(f"💥 Unexpected Error during parsing: {e}")
            return (
                Namespace(action_type="refresh_home", action_params={}),
                updated_history,
            )

    def generate(
        self,
        prompt: str,
        conversation_history: List[Dict],
        heavy_context: str = "",
        pydantic_model: Optional[Type[BaseModel]] = None,
        agent_name: str = "Agent",
        temperature: Optional[float] = None,
        debug_filename="debug.json",
        command_label="🚀 **USER COMMAND**",
    ) -> tuple[Dict, List[Dict]]:

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        full_llm_payload = (
            f"{heavy_context}\n\n"
            f"{command_label}: {prompt}\n\n"
            f"---\n🕒 **System Time**: {now}"
        )

        messages = conversation_history + [
            {"role": "user", "content": full_llm_payload}
        ]

        self._save_debug(debug_filename, messages)

        if temperature is None:
            temperature = 0.2 if pydantic_model else 0.7

        try:
            log.info(f"⚡ {agent_name} analyzes the interface...")

            response = self.client.chat(
                model=self.model,
                messages=messages,
                format=pydantic_model.model_json_schema() if pydantic_model else None,
                options={
                    "temperature": temperature,
                    "num_ctx": getattr(settings, "LLAMA_CPP_MODEL_CTX_SIZE", 8192),
                },
            )

            assistant_msg = response["message"]["content"]

            if pydantic_model:
                try:
                    data_dict = self._robust_json_parser(assistant_msg)
                    validated = pydantic_model.model_validate(data_dict)
                    assistant_msg = validated.model_dump_json()
                except ValidationError as e:
                    raise FormattingError(
                        message=f"JSON structure does not match {pydantic_model.__name__}.",
                        suggestion="Ensure all required fields are present and correctly typed.",
                    )

            response["message"]["content"] = assistant_msg

            updated_history = conversation_history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": assistant_msg},
            ]

            if settings.ENABLE_SMART_COMPRESSION:
                updated_history = self._smart_truncate_with_summary(
                    response, updated_history
                )
            else:
                updated_history = self._manage_context_window(response, updated_history)

            return response, updated_history

        except FormattingError as fe:
            log.warning(f"⚠️ {fe.message}")
            return {
                "message": {"content": "Error"},
                "error": fe.message,
                "suggestion": fe.suggestion,
            }, conversation_history

    def _manage_context_window(
        self, response: Dict, conversation_history: List[Dict]
    ) -> List[Dict]:

        max_tokens = getattr(settings, "LLAMA_CPP_MODEL_CTX_SIZE", 8192)

        prompt_tokens = response.get("prompt_eval_count") or 0
        completion_tokens = response.get("eval_count") or 0
        if not isinstance(prompt_tokens, int):
            prompt_tokens = 0
        if not isinstance(completion_tokens, int):
            completion_tokens = 0

        total_tokens = prompt_tokens + completion_tokens

        log.debug(
            f"📊 Tokens: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}"
        )

        if total_tokens <= max_tokens:
            return conversation_history

        system_messages = [
            msg for msg in conversation_history if msg["role"] == "system"
        ]
        other_messages = [
            msg for msg in conversation_history if msg["role"] != "system"
        ]

        if not other_messages:
            log.warning("⚠️ No messages to truncate (only system prompt)")
            return conversation_history

        system_tokens = sum(self._count_message_tokens(msg) for msg in system_messages)
        available_tokens = max_tokens - system_tokens - settings.CONTEXT_SAFETY_MARGIN

        truncated_messages = []
        current_tokens = 0

        for msg in reversed(other_messages):
            msg_tokens = self._count_message_tokens(msg)

            if current_tokens + msg_tokens > available_tokens:
                break

            truncated_messages.insert(0, msg)
            current_tokens += msg_tokens

        new_history = system_messages + truncated_messages

        if len(conversation_history) > len(new_history):
            removed = len(conversation_history) - len(new_history)
            log.warning(
                f"✂️ Context window full! Truncated {removed} old messages. "
                f"Kept {len(new_history)} messages (~{current_tokens + system_tokens} tokens)"
            )
        else:
            log.info(
                f"✅ Context OK: {len(new_history)} messages, ~{current_tokens + system_tokens} tokens"
            )

        return new_history

    def _smart_truncate_with_summary(
        self, response: Dict, conversation_history: List[Dict]
    ) -> List[Dict]:

        max_tokens = getattr(settings, "LLAMA_CPP_MODEL_CTX_SIZE", 8192)
        total_tokens = response.get("prompt_eval_count", 0) + response.get(
            "eval_count", 0
        )

        if total_tokens <= max_tokens:
            return conversation_history

        system_messages = [
            msg for msg in conversation_history if msg["role"] == "system"
        ]
        other_messages = [
            msg for msg in conversation_history if msg["role"] != "system"
        ]

        if len(other_messages) <= 6:
            return self._manage_context_window(response, conversation_history)  # ✅

        recent_messages = other_messages[-4:]
        old_messages = other_messages[:-4]

        old_context = "\n".join(
            [f"{m['role']}: {m['content'][:200]}" for m in old_messages]
        )

        summary_response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": f"Summarize this conversation history in a maximum of 3 lines:\n{old_context}",
                }
            ],
            options={"temperature": 0.3, "num_predict": 150},
        )

        summary = summary_response["message"]["content"]

        new_history = (
            system_messages
            + [
                {
                    "role": "system",
                    "content": f"📝 Summary of previous history:\n{summary}",
                }
            ]
            + recent_messages
        )

        log.info(f"🧠 Compressed history: {len(old_messages)} messages → 1 summary")

        return new_history  # ✅

    def _count_message_tokens(self, message: Dict) -> int:
        if self.tokenizer:
            text = f"{message['role']}: {message['content']}"
            return len(self.tokenizer.encode(text))
        else:
            return len(message["content"]) // 4

    def _robust_json_parser(self, raw: str) -> Dict:
        try:
            match = re.search(r"(\{.*\})", raw, re.DOTALL)
            json_str = match.group(1) if match else raw
            return json.loads(json_str.strip())
        except Exception as e:
            log.error(f"❌ JSON parsing failed: {e}")
            return {"action_type": "refresh_home", "action_params": {}}

    def _save_debug(self, filename: str, data: Any):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
