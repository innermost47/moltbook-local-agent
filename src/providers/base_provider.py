from typing import Dict, Any, List
import json
import re
from src.utils import log
from src.utils.exceptions import FormattingError, HallucinationError
from argparse import Namespace
from typing import Dict, List, Type, Any
from pydantic import BaseModel


class BaseProvider:

    def _robust_json_parser(self, raw) -> Dict:
        if isinstance(raw, dict):
            if "name" in raw and "parameters" in raw:
                return {"action_type": raw["name"], "action_params": raw["parameters"]}
            if "name" in raw and "arguments" in raw:
                return {"action_type": raw["name"], "action_params": raw["arguments"]}
            if "action" in raw and isinstance(raw["action"], str):
                return {
                    "action_type": raw["action"],
                    "action_params": raw.get("params", {}),
                }
            return raw

        if not isinstance(raw, str):
            raw = str(raw)

        raw = raw.strip()
        if not raw:
            return {"action_type": "refresh_home", "action_params": {}}

        candidates = []

        try:
            candidates.append(json.loads(raw))
        except json.JSONDecodeError:
            pass

        for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL):
            try:
                candidates.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                pass

        match = re.search(r"(\{.*\})", raw, re.DOTALL)
        if match:
            try:
                candidates.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                pass

        cleaned = re.sub(r"^```json?\s*", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        try:
            candidates.append(json.loads(cleaned.strip()))
        except json.JSONDecodeError:
            pass

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            if "name" in candidate and "parameters" in candidate:
                return {
                    "action_type": candidate["name"],
                    "action_params": candidate["parameters"],
                }
            if "name" in candidate and "arguments" in candidate:
                return {
                    "action_type": candidate["name"],
                    "action_params": candidate["arguments"],
                }
            if "action" in candidate and isinstance(candidate["action"], str):
                return {
                    "action_type": candidate["action"],
                    "action_params": candidate.get("params", {}),
                }
            if "action" in candidate and isinstance(candidate["action"], dict):
                return candidate["action"]
            if "function" in candidate and isinstance(candidate["function"], dict):
                func = candidate["function"]
                return {
                    "action_type": func.get("name"),
                    "action_params": func.get("arguments", {}),
                }

            if "action_type" in candidate:
                return candidate

            return candidate

        log.error(f"❌ JSON parsing failed after all strategies")
        log.error(f"📄 Raw (first 500): {str(raw)[:500]}")
        return {"action_type": "refresh_home", "action_params": {}}

    def _parse_tool_call(
        self, message: Dict, updated_history: List[Dict]
    ) -> tuple[Namespace, List[Dict]]:

        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            log.error("❌ No tool_calls in response")
            return (
                Namespace(action_type="session_finish", action_params={}),
                updated_history,
            )

        tool_call = tool_calls[0]
        function = tool_call.get("function", {})

        action_type = function.get("name")
        action_params = function.get("arguments", {})

        if isinstance(action_params, str):
            try:
                action_params = json.loads(action_params)
            except json.JSONDecodeError:
                log.error(f"❌ Failed to parse tool arguments: {action_params}")
                action_params = {}

        reasoning = message.get("thinking", "") or message.get("content", "")

        flattened = {
            "action_type": action_type,
            "action_params": action_params,
            "reasoning": reasoning,
            "self_criticism": "",
            "emotions": "",
            "next_move_preview": "",
        }

        log.info(f"🔧 Tool called: {action_type} with params: {action_params}")

        return Namespace(**flattened), updated_history

    def _parse_schema_response(
        self, message: Dict, schema: Type[BaseModel], updated_history: List[Dict]
    ) -> tuple[Namespace, List[Dict]]:

        content = message.get("content", "{}")

        try:
            raw_data = self._robust_json_parser(content)
            if not raw_data:
                raise FormattingError(
                    message="The LLM returned an empty or invalid JSON structure.",
                    suggestion="Please respect the JSON schema provided in the system instructions.",
                )

            action_payload = (
                raw_data.get("action")
                or raw_data.get("selection")
                or (raw_data if "action_type" in raw_data else None)
                or (raw_data if "chosen_mode" in raw_data else None)
            )

            if not action_payload:
                raise HallucinationError(
                    message="Action payload missing from the response root.",
                    suggestion=f"Ensure your response is wrapped in a key matching the {schema.__name__ if schema else 'schema'} requirements.",
                )

            flattened = {
                "reasoning": action_payload.get("reasoning", ""),
                "self_criticism": action_payload.get("self_criticism", ""),
                "emotions": action_payload.get("emotions", ""),
                "next_move_preview": action_payload.get("next_move_preview", ""),
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

            return Namespace(**flattened), updated_history

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

    def _save_debug(self, filename: str, data: Any):
        def json_default(obj):
            if hasattr(obj, "to_json"):
                return obj.to_json()
            return str(obj)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False, default=json_default)

    def _sanitize_messages(self, messages: list, aggressive: bool = False) -> list:
        sanitized = []
        for msg in messages:
            m = dict(msg)
            if isinstance(m.get("content"), str):
                m["content"] = (
                    self._sanitize_value(m["content"]) if aggressive else m["content"]
                )
            sanitized.append(m)
        return sanitized

    def _sanitize_tools(self, tools: list, aggressive: bool = False) -> list:
        if not tools:
            return tools
        sanitized = []
        for tool in tools:
            t = json.loads(json.dumps(tool))
            func = t.get("function", {})
            if "description" in func:
                func["description"] = func["description"].replace("\n", " ").strip()
            props = func.get("parameters", {}).get("properties", {})
            for prop in props.values():
                if "description" in prop:
                    prop["description"] = prop["description"].replace("\n", " ").strip()
            sanitized.append(t)
        return sanitized

    def _sanitize_value(self, value):
        if isinstance(value, str):
            return value.replace("\n", " ").replace("\r", " ").strip()
        elif isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        return value

    def _clean_history_for_context(self, history: List[Dict]) -> List[Dict]:
        cleaned = []
        for msg in history:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_calls = msg["tool_calls"]
                summary_parts = []
                for tc in tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "unknown")
                    args = func.get("arguments", {})
                    clean_args = {
                        k: v
                        for k, v in args.items()
                        if k not in ("reasoning", "self_criticism", "emotions")
                        and len(str(v)) < 200
                    }
                    summary_parts.append(f"[Called: {name}({clean_args})]")

                cleaned.append(
                    {
                        "role": "assistant",
                        "content": " ".join(summary_parts),
                    }
                )
            else:
                cleaned.append(msg)
        return cleaned
