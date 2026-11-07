"""
Smoke test script for Ollama local LLM integration and JSON mode.
Verifies:
1. Local Ollama server connectivity (http://127.0.0.1:11434)
2. JSON-mode schema conformance using Pydantic
3. Multimodal vision input handling (if a vision model is available)
"""

import os
import sys
import json
import base64
import time
import requests
from io import BytesIO
from pydantic import BaseModel, Field

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

class ActionSchema(BaseModel):
    action: str = Field(description="Action name, e.g., write_file, bid, emit_signal")
    task_id: str = Field(description="Target task ID")
    target: str = Field(description="Target file or section")
    reasoning: str = Field(description="Concise rationale for action")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")


def create_test_image_base64() -> str:
    """Generate a simple 64x64 colored test image in PNG format."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (64, 64), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "TEST", fill=(255, 255, 0))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except ImportError:
        # 1x1 transparent png fallback
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def test_ollama_connection() -> list[str]:
    print(f"[1/4] Checking Ollama connectivity at {OLLAMA_HOST}...")
    try:
        res = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        res.raise_for_status()
        models = [m["name"] for m in res.json().get("models", [])]
        print(f"      Success! Connected to Ollama. Available models: {models}")
        return models
    except Exception as e:
        print(f"      FAILED: Could not connect to Ollama: {e}")
        return []


def test_json_generation(model_name: str) -> bool:
    print(f"\n[2/4] Testing JSON generation with model: '{model_name}'...")
    prompt = """
You are an autonomous swarm agent. Return a valid JSON object matching this schema:
{
  "action": "write_file",
  "task_id": "task-001",
  "target": "src/index.html",
  "reasoning": "Creating the landing page hero section",
  "confidence": 0.95
}
Do not include markdown or explanations outside the JSON.
"""
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2
        }
    }

    t0 = time.time()
    try:
        res = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=60)
        res.raise_for_status()
        duration = round(time.time() - t0, 2)
        raw_response = res.json().get("response", "").strip()
        print(f"      Response received in {duration}s:")
        print(f"      {raw_response}")

        parsed_data = json.loads(raw_response)
        validated = ActionSchema(**parsed_data)
        print(f"      Validation PASSED: {validated.model_dump()}")
        return True
    except Exception as e:
        print(f"      Validation FAILED: {e}")
        return False


def test_vision_generation(model_name: str) -> bool:
    print(f"\n[3/4] Testing multimodal vision generation with model: '{model_name}'...")
    img_b64 = create_test_image_base64()
    payload = {
        "model": model_name,
        "prompt": "What colors or text do you see in this small image? Answer in 1 short sentence.",
        "images": [img_b64],
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }

    t0 = time.time()
    try:
        res = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=60)
        if res.status_code != 200:
            print(f"      Vision test returned HTTP {res.status_code}: {res.text}")
            return False
        duration = round(time.time() - t0, 2)
        text = res.json().get("response", "").strip()
        print(f"      Vision response received in {duration}s: {text}")
        return True
    except Exception as e:
        print(f"      Vision test not supported or failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Swarm Website Builder - Local LLM & JSON Smoke Test")
    print("=" * 60)

    models = test_ollama_connection()
    if not models:
        print("ERROR: No Ollama models found. Please ensure Ollama is running.")
        sys.exit(1)

    # Pick test model
    model = sys.argv[1] if len(sys.argv) > 1 else models[0]
    print(f"Target model for smoke test: {model}")

    json_ok = test_json_generation(model)
    
    # Check vision support
    vision_supported = False
    if "vl" in model.lower() or "vision" in model.lower() or "qwen3.5" in model.lower() or "llama3.2" in model.lower():
        vision_supported = test_vision_generation(model)
    else:
        print(f"\n[3/4] Skipping vision test: '{model}' is a text/code-only model.")

    print("\n" + "=" * 60)
    print(f"SMOKE TEST SUMMARY for '{model}':")
    print(f"  - Ollama Connection : PASS")
    print(f"  - JSON Generation   : {'PASS' if json_ok else 'FAIL'}")
    print(f"  - Vision Support    : {'PASS' if vision_supported else 'NOT_TESTED / NOT_SUPPORTED'}")
    print("=" * 60)

    if not json_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
