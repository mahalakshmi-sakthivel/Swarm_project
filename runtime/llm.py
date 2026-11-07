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
from pydantic import BaseModel, Field

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
    action: str = Field(description="Action name: write_file, task_done, emit_signal, task_failed")
    task_id: str = Field(description="The ID of the task being acted upon")
    target: str = Field(default="", description="Target file path or section id, e.g. index.html or #hero")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments for action (e.g. path, content)")
    signals: List[Dict[str, Any]] = Field(default_factory=list, description="Optional signals to emit on blackboard")
    reasoning_summary: str = Field(default="", description="1-line summary of agent's reasoning")


class InitialTasksPayload(BaseModel):
    tasks: List[Dict[str, Any]] = Field(description="List of initial tasks for the blackboard")


T = TypeVar("T", bound=BaseModel)


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
            schema_json = json.dumps(schema.model_json_schema(), indent=2)

            for attempt in range(max_retries + 1):
                full_system = f"{system_prompt}\n\nSTRICT JSON ENFORCEMENT:\nYou MUST return only valid JSON matching this schema:\n{schema_json}\nDo NOT wrap in markdown or add text outside the JSON object."
                
                payload = {
                    "model": self.model,
                    "system": full_system,
                    "prompt": current_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": temperature
                    }
                }

                # Run blocking requests call in threadpool
                loop = asyncio.get_running_loop()
                t0 = time.time()
                try:
                    res = await loop.run_in_executor(
                        None,
                        lambda: requests.post(f"{self.host}/api/generate", json=payload, timeout=300)
                    )
                    res.raise_for_status()
                    latency = round(time.time() - t0, 2)
                    raw_text = res.json().get("response", "").strip()

                    parsed_json = json.loads(raw_text)
                    validated_obj = schema(**parsed_json)
                    logger.info(f"LLM call succeeded on attempt {attempt+1} in {latency}s")
                    return validated_obj

                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Attempt {attempt+1} failed schema validation: {e}")
                    if attempt == max_retries:
                        raise ValueError(f"Failed to produce valid JSON after {max_retries+1} attempts: {e}")
                    
                    # Feed back error to model for retry
                    current_prompt = (
                        f"{user_prompt}\n\nYour previous response was rejected due to error:\n{str(e)}\n"
                        f"Please fix the error and output valid JSON exactly matching the schema."
                    )
