"""
LLM Client - Qwen 3.5 Interface via Ollama with JSON Validation & Retries.
Implements Non-Negotiable Rules:
- Qwen 3.5 in every agent
- Strict JSON validated with Pydantic
- Retry up to 2 times on invalid JSON, then fail the task
- Hardware-aware serialized requests (Semaphore = 1) to protect laptop GPU
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Type, TypeVar
import requests
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("runtime.llm")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen3.5:4b")

# Global lazy semaphore to serialize model calls and prevent GPU VRAM overload
_GPU_SEMAPHORE: Optional[asyncio.Semaphore] = None


def get_gpu_semaphore() -> asyncio.Semaphore:
    global _GPU_SEMAPHORE
    if _GPU_SEMAPHORE is None:
        _GPU_SEMAPHORE = asyncio.Semaphore(1)
    return _GPU_SEMAPHORE


class ActionPayload(BaseModel):
    action: str = Field(default="write_file", description="Action name: write_file, task_done, emit_signal, task_failed")
    task_id: str = Field(default="", description="The ID of the task being acted upon")
    target: str = Field(default="", description="Target file path or section id, e.g. index.html or #hero")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments for action (e.g. path, content)")
    signals: List[Dict[str, Any]] = Field(default_factory=list, description="Optional signals to emit on blackboard")
    reasoning_summary: str = Field(default="", description="1-line summary of agent's reasoning")

    @model_validator(mode="before")
    @classmethod
    def normalize_action_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If model returned "content" or "code" at top level
            if "content" in data and "args" not in data:
                data["args"] = {"content": data["content"], "path": data.get("path") or data.get("target") or data.get("filename", "")}
            elif "code" in data and "args" not in data:
                data["args"] = {"content": data["code"], "path": data.get("path") or data.get("target") or data.get("filename", "")}

            # If action is missing, default to write_file or task_done
            if not data.get("action"):
                data["action"] = "write_file" if "args" in data or "content" in data or "code" in data else "task_done"

            if not data.get("task_id"):
                data["task_id"] = "task"
        return data


class InitialTasksPayload(BaseModel):
    tasks: List[Dict[str, Any]] = Field(description="List of initial tasks for the blackboard")


T = TypeVar("T", bound=BaseModel)


def get_schema_template(schema: Type[BaseModel]) -> str:
    """Return a concrete example JSON template so small models don't echo schema metadata."""
    if schema == ActionPayload:
        return """{
  "action": "write_file",
  "task_id": "<task-id>",
  "target": "<target-file>",
  "args": {
    "path": "<target-file>",
    "content": "<FULL_FILE_CONTENT>"
  },
  "signals": [{"type": "need_qa", "target": "<target-file>"}],
  "reasoning_summary": "Summary of completed action"
}"""
    elif schema == InitialTasksPayload:
        return """{
  "tasks": [
    {
      "id": "task-01-structure",
      "title": "HTML Document Structure",
      "description": "Semantic HTML5 layout in index.html",
      "role_hint": "structure",
      "target": "index.html",
      "priority": 5
    }
  ]
}"""
    return json.dumps(schema.model_json_schema(), indent=2)


def try_repair_truncated_json(raw_text: str) -> Optional[dict]:
    """Attempt heuristic repair for JSON stream cut off near end of tokens or wrapped in fences."""
    import re
    text = raw_text.strip()
    # Strip markdown code fences if present (e.g. ```json ... ```)
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text).strip()
    text = re.sub(r"\s*```$", "", text).strip()

    if not text.startswith("{"):
        # Try finding the first { in the output
        idx = text.find("{")
        if idx != -1:
            text = text[idx:]
        else:
            return None

    # Try candidate endings to close unclosed strings and braces
    candidates = [
        "",
        '"',
        '"}',
        '"}}',
        '"]}',
        '"]}}',
        '"\n}',
        '"\n}}',
        '}\n}',
        '}}}'
    ]

    for suffix in candidates:
        candidate = text + suffix
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


class QwenClient:
    """Async wrapper for Ollama Qwen 3.5 calls with schema enforcement and bounded retries."""

    def __init__(self, model: str = DEFAULT_MODEL, host: str = OLLAMA_HOST):
        self.model = model
        self.host = host

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        max_retries: int = 2,
        temperature: float = 0.2
    ) -> T:
        """
        Request JSON generation conforming to Pydantic schema with bounded retries.
        Protects GPU via async semaphore.
        """
        async with get_gpu_semaphore():
            current_prompt = user_prompt
            template_str = get_schema_template(schema)

            for attempt in range(max_retries + 1):
                full_system = (
                    f"{system_prompt}\n\n"
                    f"CRITICAL JSON OUTPUT RULES:\n"
                    f"1. You MUST respond with ONLY a valid, raw JSON object matching this structure:\n"
                    f"{template_str}\n"
                    f"2. Fill in real values. NEVER output meta-schema words like 'properties', 'type': 'object', or '$defs'.\n"
                    f"3. Do NOT wrap in markdown fences or add explanatory text outside the JSON."
                )
                
                payload = {
                    "model": self.model,
                    "system": full_system,
                    "prompt": current_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": temperature,
                        "num_predict": 4096,
                        "num_ctx": 8192
                    }
                }

                # Run blocking requests call in threadpool
                loop = asyncio.get_running_loop()
                t0 = time.time()
                try:
                    res = await loop.run_in_executor(
                        None,
                        lambda: requests.post(f"{self.host}/api/generate", json=payload, timeout=600)
                    )
                    res.raise_for_status()
                    latency = round(time.time() - t0, 2)
                    raw_text = res.json().get("response", "").strip()

                    # Strip any accidental wrapping fences
                    import re
                    clean_text = re.sub(r"^```[a-zA-Z]*\s*", "", raw_text).strip()
                    clean_text = re.sub(r"\s*```$", "", clean_text).strip()

                    try:
                        parsed_json = json.loads(clean_text)
                    except json.JSONDecodeError as decode_err:
                        repaired = try_repair_truncated_json(raw_text)
                        if repaired is not None:
                            logger.info(f"Successfully auto-repaired truncated JSON on attempt {attempt+1}")
                            parsed_json = repaired
                        else:
                            raise decode_err

                    validated_obj = schema(**parsed_json)
                    logger.info(f"LLM call succeeded on attempt {attempt+1} in {latency}s")
                    return validated_obj

                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Attempt {attempt+1} failed schema validation: {e}")
                    if attempt == max_retries:
                        raise ValueError(f"Failed to produce valid JSON after {max_retries+1} attempts: {e}")
                    
                    # Feed back error to model for retry
                    current_prompt = (
                        f"{user_prompt}\n\n"
                        f"[RETRY NOTE - PREVIOUS OUTPUT REJECTED]: {str(e)}\n"
                        f"Fill in actual values into this structure without schema definitions:\n{template_str}\n"
                        f"Keep the file clean and concise so it does not get truncated. Ensure all quotes and strings are properly closed. Output only valid JSON."
                    )
