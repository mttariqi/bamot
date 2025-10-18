# Rough token estimation
import tiktoken

def estimate_tokens(s: str, model: str = "gpt-4o-mini") -> int:
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(s))
    except Exception:
        # fallback heuristic: 1 token ~ 4 chars
        return max(1, len(s) // 4)
