# loaders/aime.py
# AIME (2024/2025) via HuggingFace; falls back across a few mirrors.
# Sources: Maxwell-Jia/AIME_2024, math-ai/aime24, opencompass/AIME2025
# Returns: list[{"qid","question","answer"}] with answer as string.
from datasets import load_dataset
import re

AIME_CANDIDATES = ["Maxwell-Jia/AIME_2024", "math-ai/aime24", "opencompass/AIME2025"]

def _boxed(sol: str):
    if not isinstance(sol, str): return None
    m = re.search(r"\\boxed\{([^}]+)\}", sol)
    return m.group(1).strip() if m else None

def load(split: str = "test", limit: int | None = None):
    ds = None
    errors = []
    for name in AIME_CANDIDATES:
        try:
            # some AIME mirrors only have 'test' split; others 'train'
            for try_split in [split, "test", "train", "validation"]:
                try:
                    ds = load_dataset(name, split=try_split)
                    break
                except Exception as e:
                    errors.append(f"{name}:{try_split}:{e}")
            if ds is not None:
                break
        except Exception as e:
            errors.append(f"{name}:{e}")

    if ds is None:
        raise RuntimeError("AIME loader: could not fetch from HF. Tried: "
                           + "; ".join(errors))

    rows = []
    for i, x in enumerate(ds):
        qid = str(x.get("id", i))
        q = x.get("problem") or x.get("question") or x.get("prompt") or ""
        ans = x.get("answer") or _boxed(x.get("solution","")) or x.get("final_answer")
        if isinstance(ans, (int, float)): ans = str(ans)
        if ans is None: ans = ""
        rows.append({"qid": qid, "question": str(q).strip(), "answer": str(ans).strip()})
        if limit and len(rows) >= limit: break
    return rows
