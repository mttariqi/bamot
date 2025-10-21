 # loaders/strategyqa_lite.py
# StrategyQA yes/no questions. Answer normalized to "true"/"false".
from datasets import load_dataset

STRATEGYQA_CANDIDATES = ["tasksource/strategy-qa", "voidful/StrategyQA", "ChilleD/StrategyQA"]

def load(split: str = "validation", limit: int | None = None):
    ds=None; errors=[]
    for name in STRATEGYQA_CANDIDATES:
        try:
            for try_split in [split, "validation", "test", "train"]:
                try:
                    ds = load_dataset(name, split=try_split)
                    break
                except Exception as e: errors.append(f"{name}:{try_split}:{e}")
            if ds is not None: break
        except Exception as e: errors.append(f"{name}:{e}")
    if ds is None:
        raise RuntimeError("StrategyQA loader failed. " + "; ".join(errors))

    rows=[]
    for i, x in enumerate(ds):
        qid = str(x.get("id", i))
        q = x.get("question") or ""
        ans = x.get("answer")
        # normalize bool/labels to "true"/"false"
        if isinstance(ans, bool):
            ans = "true" if ans else "false"
        elif isinstance(ans, (int, float)):
            ans = "true" if ans == 1 else "false"
        else:
            s = str(ans).strip().lower()
            ans = "true" if s in {"true","yes","y","1"} else "false"
        rows.append({"qid": qid, "question": str(q).strip(), "answer": ans})
        if limit and len(rows) >= limit: break
    return rows
