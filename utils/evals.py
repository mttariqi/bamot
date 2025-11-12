# utils/evals.py
import re
import math
from typing import Optional, List
from collections import Counter

# ---------------------------
# Generic numeric utilities
# ---------------------------

def _to_float(x) -> Optional[float]:
    try:
        return float(str(x).strip())
    except Exception:
        return None

def extract_numeric_answer(text: str) -> Optional[str]:
    """
    Extract a final numeric answer from a string.
    Prefers an explicit 'ANSWER: <number>' tag; falls back to the last number.
    Returns a string so callers can stringify/compare; use _to_float() for numeric.
    """
    if not text:
        return None
    # Prefer explicit ANSWER: <number>
    m = re.search(r'ANSWER\s*:\s*(-?\d+(?:\.\d+)?)', text, flags=re.I)
    if m:
        return m.group(1)
    # Fallback to last standalone number
    nums = re.findall(r'(-?\d+(?:\.\d+)?)', text)
    return nums[-1] if nums else None

def is_correct(pred, gold) -> bool:
    """
    Generic 'numeric or string equality' checker used by most datasets
    (not StrategyQA or Game24).
    """
    if pred is None or gold is None:
        return False

    # try numeric
    pf = _to_float(pred)
    gf = _to_float(gold)
    if pf is not None and gf is not None:
        return math.isclose(pf, gf, rel_tol=1e-9, abs_tol=1e-9)

    # string fallback
    p = str(pred).strip().lower()
    g = str(gold).strip().lower()
    return p == g

# ---------------------------
# Boolean (StrategyQA) utils
# ---------------------------

def _normalize_bool(x: str) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip().lower()
    if s in {"yes", "true", "y", "1"}:
        return "yes"
    if s in {"no", "false", "n", "0"}:
        return "no"
    return None

def bool_match(pred, gold) -> bool:
    """
    StrategyQA style: compare yes/no regardless of formatting noise.
    """
    p = _normalize_bool(pred)
    g = _normalize_bool(gold)
    if p is None or g is None:
        # try to read from free text with ANSWER:
        p2 = extract_numeric_answer(str(pred))
        g2 = extract_numeric_answer(str(gold))
        return p2 == g2
    return p == g

# ---------------------------
# Game-24 evaluator
# ---------------------------

_ALLOWED_CHARS_RE = re.compile(r'^[\d\s\+\-\*/\(\)]+$')

def extract_game24_expression(text: str) -> Optional[str]:
    """
    Pull out a math-only expression from model text.
    We try several patterns; finally we take the last math-looking block.
    """
    if not text:
        return None

    # Prefer "... ANSWER: 24" and take the math block right before that
    m = re.search(r'([0-9\(\)\+\-\*/\s]+)\s*(?:=\s*24)?\s*ANSWER\s*:\s*24', text, flags=re.I)
    if m:
        expr = m.group(1).strip()
        return expr if expr else None

    # Sometimes the model uses "Expression:"
    m = re.search(r'Expression\s*:\s*([0-9\(\)\+\-\*/\s]+)', text, flags=re.I)
    if m:
        expr = m.group(1).strip()
        return expr if expr else None

    # As a fallback: take the last math-looking chunk
    candidates = re.findall(r'([0-9\(\)\+\-\*/\s]{3,})', text)
    if candidates:
        return candidates[-1].strip()

    return None

def _nums_from_str(s: str) -> List[int]:
    return [int(x) for x in re.findall(r'\b\d+\b', s)]

def _numbers_from_question(question: str) -> List[int]:
    """
    Extract the four numbers from the Game-24 question. Typical form:
    'Use 5, 5, 11, 12 with + - * / and parentheses to make 24.'
    We'll take all integers; if the last is 24, drop it. Then take the last four.
    """
    if not question:
        return []
    nums = _nums_from_str(question)
    if nums and nums[-1] == 24:
        nums = nums[:-1]
    # Some prompts contain extra numbers; keep the last four that precede 24.
    return nums[-4:]

def _uses_exact_multiset(expr: str, target_nums: List[int]) -> bool:
    """
    Check that the expression uses exactly the four given numbers (order-free).
    """
    used = Counter(_nums_from_str(expr))
    want = Counter(target_nums)
    return used == want

def _safe_eval(expr: str) -> Optional[float]:
    """
    Safely evaluate a + - * / parentheses arithmetic expression.
    Rejects anything with disallowed chars (e.g., //, **, letters).
    """
    if not expr or not _ALLOWED_CHARS_RE.match(expr):
        return None
    # Basic hard blocks
    if "**" in expr or "//" in expr:
        return None
    try:
        val = eval(expr, {"__builtins__": None}, {})
        return float(val)
    except Exception:
        return None

def is_game24_correct(pred_text: str, question: str) -> bool:
    """
    Determine correctness for Game-24:
      1) extract a math expression from pred_text,
      2) ensure only the 4 given numbers are used (multiset match),
      3) evaluate to 24 (within tolerance).
    If we cannot parse numbers from the question, we still allow correctness if
    the expression evaluates to 24.
    """
    if not pred_text:
        return False

    expr = extract_game24_expression(pred_text)
    if not expr:
        # No visible expression — as a lenient fallback, accept if explicit ANSWER: 24 exists.
        return bool(re.search(r'ANSWER\s*:\s*24', pred_text, flags=re.I))

    # Validate and evaluate
    target_nums = _numbers_from_question(question)
    if target_nums:
        if not _uses_exact_multiset(expr, target_nums):
            return False

    val = _safe_eval(expr)
    if val is None:
        return False

    return math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9)
