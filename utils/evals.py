import re
from fractions import Fraction

# -------- Helpers --------

_NUM_RE = r"ANSWER:\s*([\-]?\d+(?:\.\d+)?(?:/\d+)?)"

def _last_number_anywhere(text: str):
    m = re.findall(r"([\-]?\d+(?:\.\d+)?(?:/\d+)?)", text or "")
    return m[-1].strip() if m else None

def extract_numeric_answer(text: str):
    """
    Preferred: 'ANSWER: <number>' where <number> may be int, float, or fraction (a/b).
    Fallback: last number anywhere in the text.
    Returns normalized string (no spaces) or None.
    """
    if not text:
        return None
    m = re.findall(_NUM_RE, text)
    if m:
        return m[-1].replace(" ", "")
    # fallback to last number anywhere
    n = _last_number_anywhere(text)
    return n.replace(" ", "") if n else None

def _to_fraction(num_str: str):
    """
    Convert '3', '-2.5', '12/3' to Fraction for exact comparison.
    Floats are converted via Fraction(str(float(...))) to keep string semantics.
    Returns Fraction or None.
    """
    if num_str is None:
        return None
    s = num_str.strip()
    try:
        if "/" in s:
            return Fraction(s)  # exact rational (e.g., '12/3' -> 4)
        if "." in s:
            return Fraction(s)  # Fraction from decimal string (exact rational)
        return Fraction(int(s), 1)
    except Exception:
        try:
            # ultimate fallback: parse float then to fraction with limited denominator
            return Fraction(float(s)).limit_denominator(10_000)
        except Exception:
            return None

def is_correct(pred: str, gold: str) -> bool:
    """
    Numeric exactness with rational tolerance:
    - Try to interpret both as Fractions (handles ints, decimals, a/b forms).
    - If both parse, compare equality.
    - Else do trimmed string equality as a fallback.
    """
    if pred is None or gold is None:
        return False

    p = extract_numeric_answer(pred) if "ANSWER:" in (pred or "") else (pred or "").strip()
    g = extract_numeric_answer(gold) if "ANSWER:" in (gold or "") else (gold or "").strip()

    fp = _to_fraction(p)
    fg = _to_fraction(g)
    if fp is not None and fg is not None:
        return fp == fg

    return (p or "").strip() == (g or "").strip()

# -------- StrategyQA (unchanged semantics) --------

_STRAT_YES = {"yes", "true", "y", "t", "correct", "affirmative"}
_STRAT_NO  = {"no", "false", "n", "f", "incorrect", "negative"}

def _normalize_bool_for_strategyqa(text: str) -> str:
    s = str(text).strip().lower()
    s_alpha = re.sub(r"[^a-z]", "", s)

    if s_alpha in _STRAT_YES: return "yes"
    if s_alpha in _STRAT_NO:  return "no"

    s_digits = re.sub(r"[^0-9-]", "", s)
    if s_digits and re.fullmatch(r"-?\d+", s_digits):
        return "yes" if s_digits == "1" else "no"

    if "yes" in s: return "yes"
    if "no"  in s: return "no"

    return s_alpha or s

def bool_match(pred: str, gold: str) -> bool:
    return _normalize_bool_for_strategyqa(pred) == _normalize_bool_for_strategyqa(gold)
