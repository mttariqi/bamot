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
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 512,
        backend: str = "openai",
        llama_model_path: Optional[str] = None,
        llama_ctx: int = 4096,
        llama_threads: Optional[int] = None,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.backend = backend
        self.client = None
        self._llama = None
        # Store llama parameters for cloning
        self._llama_model_path = llama_model_path
        self._llama_ctx = llama_ctx
        self._llama_threads = llama_threads

        if backend == "openai":
            if _HAS_OPENAI:
                # Explicitly pass API key to ensure it's used
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.client = OpenAI(api_key=api_key)
                else:
                    self.client = OpenAI()  # Fallback to env var
            else:
                self.client = None
        elif backend == "llama_cpp":
            self._init_llama_cpp(llama_model_path, llama_ctx, llama_threads)
        else:
            raise ValueError(f"Unsupported backend: {backend}")

    def chat(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if self.backend == "llama_cpp":
            return self._chat_llama(system_prompt, user_prompt)

        if not self.client:
            # Check if API key is missing
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable not set. "
                    "Please set it with: export OPENAI_API_KEY='sk-...' "
                    "or create a .env file with OPENAI_API_KEY=sk-..."
                )
            # Offline fallback for dry runs, estimate tokens
            fake = f"(offline) {user_prompt[:80]} ... ANSWER: 42"
            pt = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
            return {"text": fake, "usage": {"prompt_tokens": pt, "completion_tokens": 30}}

        start = time.time()
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as e:
            end = time.time()
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise ValueError(
                    f"OpenAI API authentication failed: {error_msg}\n"
                    "Please check your OPENAI_API_KEY environment variable."
                ) from e
            raise
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

    # ----- llama.cpp backend -----
    def _init_llama_cpp(self, llama_model_path: Optional[str], llama_ctx: int, llama_threads: Optional[int]):
        try:
            from llama_cpp import Llama  # type: ignore
        except Exception as exc:
            raise ImportError(
                "llama-cpp-python is required for the llama_cpp backend. "
                "Install with: pip install llama-cpp-python"
            ) from exc

        model_path = llama_model_path or os.getenv("LLAMA_MODEL_PATH")
        if not model_path:
            raise ValueError(
                "No LLaMA model path provided. Use --llama_model_path or set LLAMA_MODEL_PATH."
            )

        self._llama = Llama(
            model_path=model_path,
            n_ctx=llama_ctx,
            n_threads=llama_threads,
            temperature=self.temperature,
        )

    def _chat_llama(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self._llama:
            raise RuntimeError("LLaMA backend not initialized")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        start = time.time()
        resp = self._llama.create_chat_completion(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        end = time.time()
        choices = resp.get("choices", [])
        if not choices:
            raise RuntimeError("LLaMA backend returned no choices")
        txt = choices[0]["message"]["content"]
        usage = resp.get("usage") or {}
        if "prompt_tokens" not in usage or usage["prompt_tokens"] is None:
            usage["prompt_tokens"] = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
        if "completion_tokens" not in usage or usage["completion_tokens"] is None:
            usage["completion_tokens"] = estimate_tokens(txt)
        return {"text": txt, "usage": usage, "latency": end - start}
