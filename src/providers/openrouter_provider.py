from datetime import datetime
from typing import Dict, List, Optional, Type
from pydantic import BaseModel
from openai import OpenAI
from argparse import Namespace
from src.settings import settings
from src.utils import log
from src.providers.base_provider import BaseProvider


class OpenRouterProvider(BaseProvider):
    def __init__(self):
        super().__init__()
        self.models = settings.FREE_MODELS
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        log.info(
            f"✨ OpenRouter Provider enabled ({len(self.models)} models in fallback chain)"
        )

    def get_next_action(
        self,
        current_context: str,
        actions_left: int,
        conversation_history: List[Dict],
        agent_name: str,
        debug_filename="debug_openrouter.json",
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
        debug_filename="debug_openrouter.json",
        command_label="🚀 **USER COMMAND**",
        max_tokens=None,
    ) -> tuple[Dict, List[Dict]]:

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        full_llm_payload = (
            f"{heavy_context}\n\n"
            f"{command_label}: {prompt}\n\n"
            f"---\n🕒 **System Time**: {now}"
        )

        messages = []
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": full_llm_payload})

        self._save_debug(debug_filename, messages)

        if temperature is None:
            temperature = 0.2 if pydantic_model or tools else 0.7

        response_format = {"type": "json_object"} if pydantic_model else None

        content = self._call_with_fallback(
            messages=messages,
            temperature=temperature,
            response_format=response_format,
            agent_name=agent_name,
            tools=tools,
        )

        if content is None:
            log.error("🔇 [FALLBACK EXHAUSTED] All models failed to respond.")
            return {
                "message": {"role": "assistant", "content": "{}"},
                "prompt_eval_count": 0,
                "eval_count": 0,
            }, conversation_history

        if hasattr(content, "tool_calls") and content.tool_calls:
            tool_calls_dict = [
                {
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in content.tool_calls
            ]
            assistant_msg = {
                "role": "assistant",
                "content": content.content or "",
                "tool_calls": tool_calls_dict,
                "thinking": "",
            }
        else:
            assistant_msg = {
                "role": "assistant",
                "content": content if isinstance(content, str) else "",
            }

        updated_history = conversation_history + [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": assistant_msg.get("content", "")},
        ]

        formatted_res = {
            "message": assistant_msg,
            "prompt_eval_count": 0,
            "eval_count": 0,
        }

        return formatted_res, updated_history

    def _call_with_fallback(
        self,
        messages: List[Dict],
        temperature: float,
        response_format: Optional[Dict],
        agent_name: str,
        tools=None,
    ) -> Optional[str]:

        for model in self.models:
            log.debug(f"📡 [GATEWAY] Sending request to {model}...")
            try:
                kwargs = dict(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=8192,
                )
                if response_format:
                    kwargs["response_format"] = response_format
                if tools:
                    kwargs["tools"] = tools
                    log.debug(
                        f"🔧 Tools sent to {model}: {[t['function']['name'] for t in tools]}"
                    )

                response = self.client.chat.completions.create(**kwargs)
                msg = response.choices[0].message
                log.info(
                    f"⚡ {agent_name} (OpenRouter/{model}) responded successfully."
                )
                if msg.tool_calls:
                    return msg
                else:
                    return msg.content

            except Exception as e:
                if "429" in str(e):
                    log.warning(
                        f"⚠️ [RATE LIMIT] {model} is unavailable (429). Trying next model..."
                    )
                    continue
                else:
                    log.error(f"❌ [ERROR] Request failed on {model}: {e}")
                    break

        return None
