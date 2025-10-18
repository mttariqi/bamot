import os, time
from typing import List, Dict, Any, Optional

# Minimal OpenAI wrapper (Responses API not required; use Chat Completions)
# If you have openai>=1.x:
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

from utils.tokens import estimate_tokens

class ModelGateway:
    """
    Thin wrapper so we can swap backends easily later (e.g., HF).
    """
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.2, max_tokens: int = 512):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI() if _HAS_OPENAI else None

    def chat(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.client:
            # Offline fallback for dry runs, estimate tokens
            fake = f"(offline) {user_prompt[:80]} ... ANSWER: 42"
            pt = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
            return {"text": fake, "usage": {"prompt_tokens": pt, "completion_tokens": 30}}

        start = time.time()
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        end = time.time()
        txt = resp.choices[0].message.content
        usage = getattr(resp, "usage", None)
        usage_dict = {"prompt_tokens": None, "completion_tokens": None}
        if usage and usage.prompt_tokens is not None and usage.completion_tokens is not None:
            usage_dict["prompt_tokens"] = usage.prompt_tokens
            usage_dict["completion_tokens"] = usage.completion_tokens
        else:
            # Fallback estimate
            usage_dict["prompt_tokens"] = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
            usage_dict["completion_tokens"] = estimate_tokens(txt)
        return {"text": txt, "usage": usage_dict, "latency": end - start}
