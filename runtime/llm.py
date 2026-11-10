"""
LLM Client - Qwen 3.5 Interface via Ollama with JSON Validation & Retries.
Implements Non-Negotiable Rules:
- Qwen 3.5 in every agent
- Strict JSON validated with Pydantic
- Retry up to 2 times on invalid JSON, then fail the task
- Hardware-aware serialized requests (Semaphore = 1) to protect laptop GPU
"""

from dataclasses import dataclass, field
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
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "qwen2.5-coder:7b")


@dataclass
class ModelConfig:
    """Configuration for local LLM inference with swappable model and task-specific parameters."""
    model_name: str = os.getenv("SWARM_MODEL", DEFAULT_MODEL)
    fallback_model: str = os.getenv("SWARM_FALLBACK_MODEL", FALLBACK_MODEL)
    code_temperature: float = 0.2
    copy_temperature: float = 0.6
    num_predict: int = 2048
    num_ctx: int = 8192

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
    """Async wrapper for Ollama Qwen 3.5 calls with schema enforcement, swappable models, and telemetry."""

    def __init__(
        self,
        model: Optional[str] = None,
        host: str = OLLAMA_HOST,
        config: Optional[ModelConfig] = None
    ):
        self.config = config or ModelConfig()
        self.model = model or self.config.model_name
        self.host = host
        # Telemetry storage: agent_id -> metrics
        self.agent_telemetry: Dict[str, Dict[str, Any]] = {}
        self.call_history: List[Dict[str, Any]] = []

    def set_model(self, model_name: str):
        """Hot-swap the active model (e.g. switch to qwen2.5-coder:7b fallback)."""
        logger.info(f"Swapping active LLM model from '{self.model}' to '{model_name}'")
        self.model = model_name
        self.config.model_name = model_name

    def record_agent_failure(self, agent_id: str):
        """Increment failure counter for a specific agent."""
        if agent_id not in self.agent_telemetry:
            self.agent_telemetry[agent_id] = {
                "total_calls": 0, "success_calls": 0, "failed_calls": 0,
                "total_eval_tokens": 0, "total_eval_duration_sec": 0.0, "avg_tokens_per_sec": 0.0
            }
        self.agent_telemetry[agent_id]["failed_calls"] += 1

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Return aggregated telemetry for tokens/sec, latency, and per-agent failures."""
        total_tokens = sum(m["total_eval_tokens"] for m in self.agent_telemetry.values())
        total_time = sum(m["total_eval_duration_sec"] for m in self.agent_telemetry.values())
        overall_tps = round(total_tokens / total_time, 2) if total_time > 0 else 0.0

        return {
            "model": self.model,
            "overall_tokens_per_sec": overall_tps,
            "total_eval_tokens": total_tokens,
            "total_calls": sum(m["total_calls"] for m in self.agent_telemetry.values()),
            "agents": self.agent_telemetry,
            "recent_calls": self.call_history[-10:]
        }

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        max_retries: int = 2,
        temperature: Optional[float] = None,
        agent_id: str = "agent-unknown",
        role_hint: Optional[str] = None
    ) -> T:
        """
        Request JSON generation conforming to Pydantic schema with bounded retries.
        Protects GPU via async semaphore. Tracks token throughput (tokens/sec) and failures per agent.
        """
        # Determine temperature by role domain (0.2 for code, 0.6 for copywriting/integration)
        if temperature is None:
            if role_hint in ("content", "coordinator", "copywriting"):
                temperature = self.config.copy_temperature
            else:
                temperature = self.config.code_temperature

        # Ensure agent telemetry structure exists
        if agent_id not in self.agent_telemetry:
            self.agent_telemetry[agent_id] = {
                "total_calls": 0, "success_calls": 0, "failed_calls": 0,
                "total_eval_tokens": 0, "total_eval_duration_sec": 0.0, "avg_tokens_per_sec": 0.0
            }

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
                        "num_predict": self.config.num_predict,
                        "num_ctx": self.config.num_ctx
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
                    res_json = res.json()
                    raw_text = res_json.get("response", "").strip()

                    # Extract Ollama tokens and eval metrics
                    eval_count = res_json.get("eval_count", 0)
                    eval_duration_ns = res_json.get("eval_duration", 0)
                    eval_sec = (eval_duration_ns / 1e9) if eval_duration_ns > 0 else latency
                    tokens_per_sec = round(eval_count / eval_sec, 2) if eval_sec > 0 and eval_count > 0 else 0.0

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

                    # Update agent telemetry on success
                    m = self.agent_telemetry[agent_id]
                    m["total_calls"] += 1
                    m["success_calls"] += 1
                    m["total_eval_tokens"] += eval_count
                    m["total_eval_duration_sec"] += eval_sec
                    if m["total_eval_duration_sec"] > 0:
                        m["avg_tokens_per_sec"] = round(m["total_eval_tokens"] / m["total_eval_duration_sec"], 2)

                    self.call_history.append({
                        "agent_id": agent_id,
                        "role_hint": role_hint,
                        "model": self.model,
                        "latency": latency,
                        "eval_tokens": eval_count,
                        "tokens_per_sec": tokens_per_sec,
                        "status": "success",
                        "attempt": attempt + 1
                    })

                    logger.info(
                        f"LLM call succeeded for '{agent_id}' on attempt {attempt+1} in {latency}s "
                        f"({tokens_per_sec} tokens/sec, {eval_count} tokens, temp={temperature})"
                    )
                    return validated_obj

                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Attempt {attempt+1} for '{agent_id}' failed validation: {e}")
                    if attempt == max_retries:
                        self.agent_telemetry[agent_id]["total_calls"] += 1
                        self.agent_telemetry[agent_id]["failed_calls"] += 1
                        self.call_history.append({
                            "agent_id": agent_id,
                            "role_hint": role_hint,
                            "model": self.model,
                            "latency": round(time.time() - t0, 2),
                            "status": "failed",
                            "error": str(e),
                            "attempts": max_retries + 1
                        })
                        raise ValueError(f"Failed to produce valid JSON after {max_retries+1} attempts: {e}")
                    
                    # Feed back error to model for retry
                    current_prompt = (
                        f"{user_prompt}\n\n"
                        f"[RETRY NOTE - PREVIOUS OUTPUT REJECTED]: {str(e)}\n"
                        f"Fill in actual values into this structure without schema definitions:\n{template_str}\n"
                        f"Keep the file clean and concise so it does not get truncated. Ensure all quotes and strings are properly closed. Output only valid JSON."
                    )
