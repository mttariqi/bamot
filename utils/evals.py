import re

def extract_numeric_answer(text: str):
    """
    Expect pattern 'ANSWER: <number>'
    Return as string normalized (strip spaces).
    """
    m = re.findall(r"ANSWER:\s*([\-]?\d+(?:\.\d+)?)", text)
    if not m:
        # Try final number fallback
        m = re.findall(r"([\-]?\d+(?:\.\d+)?)", text)
        return m[-1].strip() if m else None
    return m[-1].strip()

def is_correct(pred: str, gold: str) -> bool:
    """Simple numeric exact match (string compare after stripping)."""
    if pred is None:
        return False
    return pred.strip() == str(gold).strip()
# === Boolean evaluation for StrategyQA (append-only) ===


_STRAT_YES = {"yes", "true", "y", "t", "correct"}
_STRAT_NO  = {"no", "false", "n", "f", "incorrect"}

def _normalize_bool_for_strategyqa(text: str) -> str:
    s = re.sub(r"[^a-z]", "", str(text).lower())
    if s in _STRAT_YES: return "yes"
    if s in _STRAT_NO:  return "no"
    return s  # fallback (will likely not match)

def bool_match(pred: str, gold: str) -> bool:
    """Return True iff pred and gold are the same normalized yes/no."""
    return _normalize_bool_for_strategyqa(pred) == _normalize_bool_for_strategyqa(gold)
