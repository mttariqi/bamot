 # loaders/math500.py
# MATH-500 (curated subset of Hendrycks MATH) via HuggingFaceH4/MATH-500.
# Normalizes to numeric/string answer; attempts to extract \boxed{...} when needed.
from datasets import load_dataset
import re

def _boxed(sol: str):
    if not isinstance(sol, str): return None
    m = re.search(r"\\boxed\{([^}]+)\}", sol)
    return m.group(1).strip() if m else None

def load(split: str = "test", limit: int | None = None):
    try:
        ds = load_dataset("HuggingFaceH4/MATH-500", split=split)
    except Exception:
        # some mirrors only have 'test'; try alternates
        for try_split in ["test", "validation", "train"]:
            try:
                ds = load_dataset("HuggingFaceH4/MATH-500", split=try_split)
                break
            except Exception:
                ds = None
        if ds is None:
            raise
    rows=[]
    for i, x in enumerate(ds):
        qid = str(x.get("id", i))
        q = x.get("problem") or x.get("question") or ""
        ans = x.get("answer") or _boxed(x.get("solution","")) or x.get("final_answer") or ""
        rows.append({"qid": qid, "question": str(q).strip(), "answer": str(ans).strip()})
        if limit and len(rows) >= limit: break
    return rows
