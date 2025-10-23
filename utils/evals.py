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

_STRAT_YES = {"yes", "true", "y", "t", "correct", "affirmative"}
_STRAT_NO  = {"no", "false", "n", "f", "incorrect", "negative"}

def _normalize_bool_for_strategyqa(text: str) -> str:
    s = str(text).strip().lower()
    # Strip non-letters/numbers for flexible matching
    s_alpha = re.sub(r"[^a-z]", "", s)

    # 1) direct word forms
    if s_alpha in _STRAT_YES: return "yes"
    if s_alpha in _STRAT_NO:  return "no"

    # 2) pure digits? map common numeric encodings
    #    Convention: "1" => yes; all other digits => no (since task is binary)
    s_digits = re.sub(r"[^0-9-]", "", s)
    if s_digits and re.fullmatch(r"-?\d+", s_digits):
        return "yes" if s_digits == "1" else "no"

    # 3) fallback: if the raw string literally contains "yes" / "no"
    if "yes" in s: return "yes"
    if "no"  in s: return "no"

    # 4) default (won't match and will be marked incorrect)
    return s_alpha or s

def bool_match(pred: str, gold: str) -> bool:
    return _normalize_bool_for_strategyqa(pred) == _normalize_bool_for_strategyqa(gold)