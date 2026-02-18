import json
import re
import httpx
from datetime import datetime
from typing import Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError
from ollama import Client
import tiktoken
from src.settings import settings
from src.utils import log
from src.utils.exceptions import FormattingError
from argparse import Namespace
from src.providers.base_provider import BaseProvider


class OllamaProvider(BaseProvider):
    def __init__(self, model: str = "qwen2.5:7b"):
        super().__init__()
        self.model = model

        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
            log.warning("⚠️ tiktoken not available, falling back to Ollama count")

        if settings.USE_OLLAMA_PROXY:
            proxy_url = getattr(settings, "OLLAMA_PROXY_URL", "http://localhost:8000")
            api_key = settings.OLLAMA_PROXY_API_KEY
            self.client = Client(
                host=proxy_url,
                headers={"X-API-Key": api_key},
                timeout=httpx.Timeout(None),
            )
            log.info(f"🌐 Ollama Generator PROXY mode enabled to {proxy_url}")
        else:
            self.client = Client(
                host="http://localhost:11434",
                timeout=httpx.Timeout(None),
            )
            log.info("🏠 LOCAL Mode enabled (Direct Ollama)")

    def get_next_action(
        self,
        current_context: str,
        actions_left: int,
        conversation_history: List[Dict],
        agent_name: str,
        debug_filename="debug.json",
        schema: Type[BaseModel] = None,
        tools=None,
        max_tokens=None,
    ) -> tuple[Namespace, List[Dict]]:

        prompt = f"Analyze the dashboard and decide your next move. Actions left: {actions_left}/{settings.MAX_ACTIONS_PER_SESSION}"

        response, updated_history = self.generate(
            prompt=prompt,
            heavy_context=current_context,
            pydantic_model=schema,
            tools=tools,
            agent_name=agent_name,
            conversation_history=conversation_history,
            debug_filename=debug_filename,
            command_label="🚀 **USER COMMAND**",
            max_tokens=max_tokens,
        )

        message = response.get("message", {})

        if tools and message.get("tool_calls"):
            return self._parse_tool_call(message, updated_history)
        else:
            return self._parse_schema_response(message, schema, updated_history)

    def generate(
        self,
        prompt: str,
        conversation_history: List[Dict],
        heavy_context: str = "",
        pydantic_model: Optional[Type[BaseModel]] = None,
        tools=None,
        agent_name: str = "Agent",
        temperature: Optional[float] = None,
        debug_filename="debug.json",
        command_label="🚀 **USER COMMAND**",
        max_tokens=None,
    ) -> tuple[Dict, List[Dict]]:

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        full_llm_payload = (
            f"{heavy_context}\n\n"
            f"{command_label}: {prompt}\n\n"
            f"---\n🕒 **System Time**: {now}"
        )

        messages = self._clean_history_for_context(conversation_history) + [
            {"role": "user", "content": full_llm_payload}
        ]

        self._save_debug(debug_filename, messages)

        if temperature is None:
            temperature = 0.2 if pydantic_model or tools else 0.7

        try:
            log.info(f"⚡ {agent_name} analyzes the interface...")
            if tools:
                tools = self._sanitize_tools(tools)

            messages = self._sanitize_messages(messages)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.chat(
                        model=self.model,
                        messages=messages,
                        format=(
                            pydantic_model.model_json_schema()
                            if pydantic_model
                            else None
                        ),
                        options={
                            "temperature": temperature,
                            "num_ctx": getattr(settings, "NUM_CTX_OLLAMA", 8192),
                            "num_predict": (
                                max_tokens if max_tokens is not None else 2048
                            ),
                        },
                        tools=tools if tools else None,
                    )
                    break

                except Exception as e:
                    error_str = str(e)

                    if "not found" in error_str and "tool" in error_str:
                        log.error(f"❌ Tool not found in current context: {error_str}")
                        log.warning(
                            "⚠️ This is likely a stale tool_call in history — returning fallback"
                        )
                        return {
                            "message": {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "refresh_home",
                                            "arguments": {},
                                        }
                                    }
                                ],
                            }
                        }, conversation_history

                    elif "invalid character" in error_str and attempt < max_retries - 1:
                        log.warning(
                            f"⚠️ Ollama serialization error (attempt {attempt+1}/{max_retries}), sanitizing harder..."
                        )
                        messages = self._sanitize_messages(messages, aggressive=True)
                        if tools:
                            tools = self._sanitize_tools(tools, aggressive=True)

                    elif attempt == max_retries - 1:
                        log.error(f"❌ All {max_retries} attempts failed: {e}")
                        raise

                    else:
                        raise

            message = response["message"]

            if tools and message.get("tool_calls"):
                tool_calls_serializable = []
                for tc in message.get("tool_calls", []):
                    if hasattr(tc, "__dict__"):
                        tc_dict = {
                            "id": getattr(tc, "id", None),
                            "function": {
                                "name": (
                                    getattr(tc.function, "name", None)
                                    if hasattr(tc, "function")
                                    else None
                                ),
                                "arguments": (
                                    getattr(tc.function, "arguments", {})
                                    if hasattr(tc, "function")
                                    else {}
                                ),
                            },
                        }
                    else:
                        tc_dict = tc
                    tool_calls_serializable.append(tc_dict)

                assistant_msg = {
                    "role": "assistant",
                    "content": message.get("thinking", "")
                    or message.get("content", ""),
                    "tool_calls": tool_calls_serializable,
                }
            else:
                content = message.get("content", "")
                thinking = message.get("thinking", "")

                if not content and thinking:
                    log.warning(
                        "⚠️ Qwen3 thinking mode detected - extracting from thinking"
                    )
                    match = re.search(r"(\{.*\})", thinking, re.DOTALL)
                    if match:
                        content = match.group(1)
                        log.info(f"✅ Extracted content from thinking: {content[:100]}")
                    else:
                        log.error("❌ No JSON found in thinking block!")

                assistant_msg = {
                    "role": "assistant",
                    "content": content,
                }

                if pydantic_model and content:
                    try:
                        data_dict = self._robust_json_parser(content)
                        validated = pydantic_model.model_validate(data_dict)
                        assistant_msg = {
                            "role": "assistant",
                            "content": validated.model_dump_json(),
                        }
                    except ValidationError as e:
                        log.warning(
                            f"⚠️ JSON structure does not match {pydantic_model.__name__}."
                        )

                elif pydantic_model and not content:
                    log.error(
                        "❌ Empty content even after thinking extraction - fallback!"
                    )
                    assistant_msg = {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "action": {
                                    "action_type": "refresh_home",
                                    "action_params": {},
                                }
                            }
                        ),
                    }

            updated_history = conversation_history + [
                {"role": "user", "content": prompt},
                assistant_msg,
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

        max_tokens = getattr(settings, "NUM_CTX_OLLAMA", 8192)

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

        max_tokens = getattr(settings, "NUM_CTX_OLLAMA", 8192)
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
