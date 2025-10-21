 # loaders/asdiv.py
# ASDiv via HuggingFace (several mirrors). Normalizes to {qid, question, answer}
from datasets import load_dataset

ASDIV_CANDIDATES = ["EleutherAI/asdiv", "yimingzhang/asdiv", "nguyen-brat/asdiv"]

def load(split: str = "test", limit: int | None = None):
    ds=None; errors=[]
    for name in ASDIV_CANDIDATES:
        try:
            for try_split in [split, "test", "validation", "train"]:
                try:
                    ds = load_dataset(name, split=try_split)
                    break
                except Exception as e: errors.append(f"{name}:{try_split}:{e}")
            if ds is not None: break
        except Exception as e: errors.append(f"{name}:{e}")
    if ds is None:
        raise RuntimeError("ASDiv loader failed. " + "; ".join(errors))

    rows=[]
    for i, x in enumerate(ds):
        qid = str(x.get("id", i))
        q = x.get("question") or x.get("Question") or ""
        # common keys: "answer", sometimes list; prefer first if list
        ans = x.get("answer") or x.get("Answer") or x.get("final_answer") or ""
        if isinstance(ans, list): ans = ans[0] if ans else ""
        rows.append({"qid": qid, "question": str(q).strip(), "answer": str(ans).strip()})
        if limit and len(rows) >= limit: break
    return rows
