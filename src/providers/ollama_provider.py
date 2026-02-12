import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Type, Any
from pydantic import BaseModel, ValidationError
from ollama import Client
from src.settings import settings
from src.utils import log
from src.utils.exceptions import FormattingError, HallucinationError
from argparse import Namespace


class OllamaProvider:
    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model
        self.conversation_history: List[Dict] = []

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
        agent_name: str,
    ) -> Namespace:

        prompt = f"Analyze the dashboard and decide your next move. Energy: {actions_left}/10"

        response = self.generate(
            prompt=prompt,
            heavy_context=current_context,
            pydantic_model=schema,
            agent_name=agent_name,
            save_to_history=True,
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

            return Namespace(**flattened)

        except (FormattingError, HallucinationError) as e:
            log.warning(f"⚠️ {type(e).__name__}: {e.message}")
            return Namespace(
                action_type="refresh_home",
                action_params={"error_suggestion": e.suggestion},
                reasoning=f"Error: {e.message}",
            )
        except Exception as e:
            log.error(f"💥 Unexpected Error during parsing: {e}")
            return Namespace(action_type="refresh_home", action_params={})

    def generate(
        self,
        prompt: str,
        heavy_context: str = "",
        pydantic_model: Optional[Type[BaseModel]] = None,
        save_to_history: bool = True,
        agent_name: str = "Agent",
        temperature: Optional[float] = None,
    ) -> Dict:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if not self.conversation_history:
            system_content = self.get_system_prompt()
            allowed_types = []
            if hasattr(pydantic_model, "model_json_schema"):
                schema = pydantic_model.model_json_schema()
                mapping = (
                    schema.get("properties", {})
                    .get("action", {})
                    .get("discriminator", {})
                    .get("mapping", {})
                )
                allowed_types = list(mapping.keys())

            STRICT_JSON_SUFFIX = (
                "\n\n### ⚠️ MANDATORY TECHNICAL CONSTRAINT\n"
                "1. Your response MUST be a single, valid JSON object.\n"
                "2. You MUST include the 'action_type' field inside the 'action' object.\n"
                f"3. ALLOWED action_type values: {', '.join(allowed_types)}\n"
                "4. DO NOT include any text before or after the JSON.\n"
                "5. If you navigate, you MUST also include 'chosen_mode' and 'expected_actions_count'."
            )
            system_content += STRICT_JSON_SUFFIX
            if system_content:
                self.conversation_history.append(
                    {"role": "system", "content": system_content}
                )
            else:
                log.warning(
                    "⚠️ No system prompt file found. Running without instructions."
                )

        full_llm_payload = (
            f"{heavy_context}\n\n"
            f"🚀 **USER COMMAND**: {prompt}\n\n"
            f"---\n🕒 **System Time**: {now}"
        )

        messages = self.conversation_history + [
            {"role": "user", "content": full_llm_payload}
        ]

        self._save_debug(
            f"debug_{agent_name.lower()}_{int(time.time())}.json", messages
        )

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
                    "num_ctx": getattr(settings, "NUM_CTX_OLLAMA", 8192),
                },
            )

            self._manage_context_window(response)

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

            if save_to_history:
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append(
                    {"role": "assistant", "content": assistant_msg}
                )

            response["message"]["content"] = assistant_msg
            return response

        except FormattingError as fe:
            log.warning(f"⚠️ {fe.message}")
            return {
                "message": {"content": "Error"},
                "error": fe.message,
                "suggestion": fe.suggestion,
            }

    def _manage_context_window(self, response: Dict):
        total_tokens = response.get("prompt_eval_count", 0) + response.get(
            "eval_count", 0
        )
        max_tokens = getattr(settings, "MAX_SESSION_TOKENS", 6000)

        if total_tokens > max_tokens and len(self.conversation_history) > 4:
            log.warning(f"✂️ Context full ({total_tokens} tokens). Clearing history...")
            self.conversation_history = (
                self.conversation_history[:2] + self.conversation_history[-4:]
            )

    def _robust_json_parser(self, raw: str) -> Dict:
        try:
            match = re.search(r"(\{.*\})", raw, re.DOTALL)
            json_str = match.group(1) if match else raw
            return json.loads(json_str.strip())
        except Exception as e:
            log.error(f"❌ JSON parsing failed: {e}")
            return {"action_type": "refresh_home", "action_params": {}}

    def _save_debug(self, filename: str, data: Any):
        os.makedirs("logs/debug", exist_ok=True)
        path = os.path.join("logs/debug", filename)
        with open("debug.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_system_prompt(self):
        system_prompt = ""

        if os.path.exists(settings.MAIN_AGENT_FILE_PATH):
            with open(settings.MAIN_AGENT_FILE_PATH, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        elif os.path.exists(settings.BASE_AGENT_FILE_PATH):
            with open(settings.BASE_AGENT_FILE_PATH, "r", encoding="utf-8") as f:
                system_prompt = f.read()

        return system_prompt
