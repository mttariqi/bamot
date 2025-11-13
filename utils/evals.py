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

    FIX: now robust to 'ANSWER: 42' style outputs by first extracting a number
    from free text for both pred and gold when direct float() fails.
    """
    if pred is None or gold is None:
        return False

    # 1) direct numeric parse
    pf = _to_float(pred)
    gf = _to_float(gold)

    # 2) if either failed, try extracting numeric from text then parse
    if pf is None:
        pnum = extract_numeric_answer(str(pred))
        pf = _to_float(pnum) if pnum is not None else None
    if gf is None:
        gnum = extract_numeric_answer(str(gold))
        gf = _to_float(gnum) if gnum is not None else None

    if pf is not None and gf is not None:
        return math.isclose(pf, gf, rel_tol=1e-9, abs_tol=1e-9)

    # 3) string fallback (case-insensitive, trimmed)
    p = str(pred).strip().lower()
    g = str(gold).strip().lower()
    return p == g

# ---------------------------
# Boolean (StrategyQA) utils
# ---------------------------

def _normalize_bool(x: str) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip().lower().strip(".!,;:")
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
    if p is not None and g is not None:
        return p == g

    # Try to salvage from free text like "ANSWER: yes"
    p2 = _normalize_bool(str(pred))
    g2 = _normalize_bool(str(gold))
    if p2 is not None and g2 is not None:
        return p2 == g2

    return False

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
    return [int(x) for x in re.findall(r'\b\d+\b', s or "")]

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
    return nums[-4:]

def _uses_exact_multiset(expr: str, target_nums: List[int]) -> bool:
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

    expr = extract_game24_expression(pred_text) or pred_text  # allow passing bare expr
    if not expr:
        # No visible expression — as a lenient fallback, accept if explicit ANSWER: 24 exists.
        return bool(re.search(r'ANSWER\s*:\s*24', pred_text, flags=re.I))

    target_nums = _numbers_from_question(question)
    if target_nums and not _uses_exact_multiset(expr, target_nums):
        return False

    val = _safe_eval(expr)
    if val is None:
        return False

    return math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9)
