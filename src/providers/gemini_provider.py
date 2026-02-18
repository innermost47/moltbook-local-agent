from datetime import datetime
from typing import Dict, List, Optional, Type
from pydantic import BaseModel
from google import genai
from google.genai import types
from argparse import Namespace
import time
from src.settings import settings
from src.utils import log
from src.providers.base_provider import BaseProvider


class GeminiProvider(BaseProvider):
    def __init__(self, model: str = "gemini-2.0-flash"):
        super().__init__()
        self.model_name = model
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        log.info(f"✨ Gemini Provider enabled ({self.model_name})")

    def get_next_action(
        self,
        current_context: str,
        actions_left: int,
        conversation_history: List[Dict],
        agent_name: str,
        debug_filename="debug_gemini.json",
        schema: Type[BaseModel] = None,
        tools=None,
    ) -> tuple[Namespace, List[Dict]]:

        prompt = f"Analyze the dashboard and decide your next move. Actions left: {actions_left}/{settings.MAX_ACTIONS_PER_SESSION}"
        log.debug(f"⏳ [COOLDOWN] API rate limit protection: sleeping for 4s...")
        time.sleep(4)
        log.debug(
            f"📡 [GATEWAY] Cooldown expired. Sending request to {self.model_name}..."
        )
        response, updated_history = self.generate(
            prompt=prompt,
            heavy_context=current_context,
            pydantic_model=schema,
            tools=tools,
            agent_name=agent_name,
            conversation_history=conversation_history,
            debug_filename=debug_filename,
            command_label="🚀 **USER COMMAND**",
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
        debug_filename="debug_gemini.json",
        command_label="🚀 **USER COMMAND**",
    ) -> tuple[Dict, List[Dict]]:

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        full_llm_payload = (
            f"{heavy_context}\n\n"
            f"{command_label}: {prompt}\n\n"
            f"---\n🕒 **System Time**: {now}"
        )

        gemini_history = []
        for msg in conversation_history:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            gemini_history.append(
                types.Content(role=role, parts=[types.Part(text=msg["content"])])
            )

        gemini_history.append(
            types.Content(role="user", parts=[types.Part(text=full_llm_payload)])
        )

        debug_data = []
        for msg in gemini_history:
            debug_data.append(
                {"role": msg.role, "parts": [{"text": p.text} for p in msg.parts]}
            )
        self._save_debug(debug_filename, debug_data)

        if temperature is None:
            temperature = 0.2 if pydantic_model or tools else 0.7

        config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=0.95,
            top_k=64,
            max_output_tokens=8192,
            response_mime_type="application/json" if pydantic_model else "text/plain",
            response_schema=pydantic_model if pydantic_model else None,
        )

        try:
            log.info(f"⚡ {agent_name} (Gemini) analyzes the interface...")

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=gemini_history,
                config=config,
            )

            content = response.text

            assistant_msg = {
                "role": "assistant",
                "content": content,
            }

            updated_history = conversation_history + [
                {"role": "user", "content": prompt},
                assistant_msg,
            ]

            formatted_res = {
                "message": assistant_msg,
                "prompt_eval_count": response.usage_metadata.prompt_token_count or 0,
                "eval_count": response.usage_metadata.candidates_token_count or 0,
            }

            return formatted_res, updated_history

        except Exception as e:
            log.error(f"💥 Gemini Execution Error: {e}")
            return {
                "message": {"content": "{}"},
                "prompt_eval_count": 0,
                "eval_count": 0,
            }, conversation_history
