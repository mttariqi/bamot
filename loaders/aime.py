# loaders/aime.py
# Robust AIME loader that tries multiple mirrors and normalizes {qid, question, answer}.
# Extracts answers from common fields OR from LaTeX-style solutions via \boxed{...} or "Answer: ...".
from datasets import load_dataset
import re

AIME_CANDIDATES = [
    "Maxwell-Jia/AIME_2024",
    "math-ai/aime24",
    "opencompass/AIME2025",
    "opencompass/AIME2024",
    "Wasmachstdugerne/AIME",
]

_BOXED_RE = re.compile(r"\\boxed\{([^}]*)\}")
_ANS_RE   = re.compile(r"(?i)\b(?:final\s*answer|answer)\s*[:=]\s*([^\n\r\.]+)")

def _norm(s):
    return str(s).strip() if s is not None else ""

def _extract_answer(x):
    # Common direct fields
    for key in ["answer", "final_answer", "ans", "label", "target", "gold", "gt_answer", "expected"]:
        if key in x and x[key] not in (None, ""):
            return _norm(x[key])
    # Some mirrors put numeric under different key
    for key in ["answer_number", "answerNumber", "A"]:
        if key in x and x[key] not in (None, ""):
            return _norm(x[key])
    # Try parsing from solution text
    sol = _norm(x.get("solution") or x.get("solutions") or x.get("explanation") or "")
    if sol:
        m = _BOXED_RE.search(sol)
        if m:
            return _norm(m.group(1))
        m = _ANS_RE.search(sol)
        if m:
            return _norm(m.group(1))
    # As a last resort some dumps have "choices" with correct index
    if "choices" in x and "correct" in x:
        try:
            idx = int(x["correct"])
            return _norm(x["choices"][idx])
        except Exception:
            pass
    return ""  # let caller log empty; is_correct will treat as wrong

def _extract_question(x):
    # Typical AIME mirrors
    return _norm(
        x.get("problem") or
        x.get("question") or
        x.get("prompt") or
        x.get("stem") or
        ""
    )

def load(split: str = "test", limit: int | None = None):
    ds = None
    errs = []
    for name in AIME_CANDIDATES:
        try:
            for try_split in [split, "test", "validation", "dev", "train"]:
                try:
                    ds = load_dataset(name, split=try_split)
                    break
                except Exception as e:
                    errs.append(f"{name}:{try_split}:{e}")
            if ds is not None:
                break
        except Exception as e:
            errs.append(f"{name}:{e}")
    if ds is None:
        raise RuntimeError("AIME loader failed. Tried mirrors:\n  " + "\n  ".join(errs))

    out = []
    for i, x in enumerate(ds):
        qid = _norm(x.get("id", x.get("index", x.get("qid", i))))
        q   = _extract_question(x)
        ans = _extract_answer(x)
        out.append({"qid": qid, "question": q, "answer": ans})
        if limit and len(out) >= limit:
            break
    return out
