import ast
import math
import operator
import re
from typing import Optional

# --------------------------
# Core extraction utilities
# --------------------------

_ANS_TAG = re.compile(r"(?:^|\b)ANSWER\s*:\s*([^\n\r]+)", re.IGNORECASE)
_NUM_TOKEN = re.compile(r"[-+]?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?")

def extract_numeric_answer(text: str) -> Optional[str]:
    """
    Prefer the last 'ANSWER: <value>' if present.
    Fallback: last numeric-like token anywhere in the text.
    Returns a string (not float) so caller controls formatting.
    """
    if not text:
        return None
    m = _ANS_TAG.findall(text)
    if m:
        return m[-1].strip()
    toks = _NUM_TOKEN.findall(text)
    return toks[-1].strip() if toks else None

def _parse_fraction_or_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    if "/" in s:
        try:
            a, b = s.split("/", 1)
            return float(a) / float(b)
        except Exception:
            return None
    try:
        return float(s)
    except Exception:
        return None

def _numbers_equal(a: str, b: str, tol: float = 1e-6) -> bool:
    ax = _parse_fraction_or_float(a)
    bx = _parse_fraction_or_float(b)
    if ax is None or bx is None:
        # fall back to normalized string
        return (a or "").strip() == (b or "").strip()
    return abs(ax - bx) <= tol

# --------------------------
# StrategyQA boolean utils
# --------------------------

_STRAT_YES = {"yes", "true", "y", "t", "correct", "affirmative"}
_STRAT_NO  = {"no", "false", "n", "f", "incorrect", "negative"}

def _normalize_bool_for_strategyqa(text: str) -> str:
    s = str(text or "").strip().lower()
    s_alpha = re.sub(r"[^a-z]", "", s)

    if s_alpha in _STRAT_YES: return "yes"
    if s_alpha in _STRAT_NO:  return "no"

    # numeric encodings (loose): "1" => yes, else no
    s_digits = re.sub(r"[^0-9-]", "", s)
    if s_digits and re.fullmatch(r"-?\d+", s_digits):
        return "yes" if s_digits == "1" else "no"

    if "yes" in s: return "yes"
    if "no"  in s: return "no"

    return s_alpha or s

def bool_match(pred: str, gold: str) -> bool:
    return _normalize_bool_for_strategyqa(pred) == _normalize_bool_for_strategyqa(gold)

# --------------------------
# Game-24: safe expression eval
# --------------------------

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def _safe_eval_expr(expr: str) -> Optional[float]:
    try:
        node = ast.parse(expr, mode="eval")
    except Exception:
        return None

    def _eval(n):
        if isinstance(n, ast.Expression): return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if hasattr(ast, "Num") and isinstance(n, ast.Num):  # py<3.8
            return float(n.n)
        if isinstance(n, ast.BinOp):
            left = _eval(n.left); right = _eval(n.right)
            if left is None or right is None: return None
            op = _ALLOWED_OPS.get(type(n.op))
            if not op: return None
            try:
                return float(op(left, right))
            except Exception:
                return None
        if isinstance(n, ast.UnaryOp):
            val = _eval(n.operand)
            if val is None: return None
            op = _ALLOWED_OPS.get(type(n.op))
            if not op: return None
            try:
                return float(op(val))
            except Exception:
                return None
        # disallow calls, names, subscripts, etc.
        return None

    return _eval(node)

def game24_is_24(pred: str) -> bool:
    """
    True if:
      - contains 'ANSWER: 24', OR
      - contains a line with an arithmetic expression that evaluates to 24 (±1e-6).
    """
    if not pred:
        return False

    # Direct final tag
    m = _ANS_TAG.search(pred)
    if m and _numbers_equal(m.group(1), "24"):
        return True

    # Heuristic: scan lines bottom-up for an operator-bearing expression
    lines = [ln.strip() for ln in pred.strip().splitlines() if ln.strip()]
    for line in reversed(lines):
        if any(op in line for op in ["+", "-", "*", "/"]):
            # strip anything after '=>' or 'ANSWER:'
            line = re.split(r"(?:=>|ANSWER\s*:)", line, flags=re.IGNORECASE)[0].strip()
            val = _safe_eval_expr(line)
            if val is not None and abs(val - 24.0) <= 1e-6:
                return True
    return False

# --------------------------
# General correctness
# --------------------------

def is_correct(pred: str, gold: str) -> bool:
    """
    Robust correctness:
      * If gold is clearly boolean (yes/no/true/false) → boolean normalization.
      * If gold == '24' → allow Game-24 expression success or final numeric 24.
      * Else: numeric compare (with tolerance) if both are numbers; otherwise exact string match after trimming.
    """
    if pred is None:
        return False

    gold_s = (gold or "").strip().lower()
    if gold_s in {"yes", "no", "true", "false"}:
        return bool_match(pred, gold)

    if (gold or "").strip() == "24":
        if game24_is_24(pred):
            return True
        # fallback: numeric 24 check
        pfin = extract_numeric_answer(pred) or pred
        return _numbers_equal(pfin, "24")

    pfin = extract_numeric_answer(pred) or pred
    gfin = extract_numeric_answer(gold) or gold

    # numeric compare if both look numeric-like
    if _NUM_TOKEN.fullmatch(str(pfin).strip() or "") and _NUM_TOKEN.fullmatch(str(gfin).strip() or ""):
        return _numbers_equal(str(pfin), str(gfin))

    return (str(pfin).strip()) == (str(gfin).strip())
