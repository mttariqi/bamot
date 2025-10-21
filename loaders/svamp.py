 # loaders/svamp.py
# SVAMP via HuggingFace (tries a few mirrors). Fields differ by mirror; we normalize.
# Returns: list[{"qid","question","answer"}]
from datasets import load_dataset

SVAMP_CANDIDATES = ["MU-NLPC/Calc-svamp", "ChilleD/SVAMP", "tongyx361/svamp"]

def _mk_question(x):
    # many SVAMP mirrors expose Body + Question; some just question
    body = x.get("Body") or x.get("body") or ""
    q = x.get("Question") or x.get("question") or ""
    return (str(body).strip() + " " + str(q).strip()).strip()

def load(split: str = "test", limit: int | None = None):
    ds = None; errors=[]
    for name in SVAMP_CANDIDATES:
        try:
            for try_split in [split, "test", "validation", "train"]:
                try:
                    ds = load_dataset(name, split=try_split)
                    break
                except Exception as e: errors.append(f"{name}:{try_split}:{e}")
            if ds is not None: break
        except Exception as e: errors.append(f"{name}:{e}")
    if ds is None:
        raise RuntimeError("SVAMP loader failed. " + "; ".join(errors))

    rows=[]
    for i, x in enumerate(ds):
        qid = str(x.get("id", i))
        question = _mk_question(x)
        ans = x.get("Answer") or x.get("answer") or x.get("final_answer") or ""
        rows.append({"qid": qid, "question": question, "answer": str(ans).strip()})
        if limit and len(rows) >= limit: break
    return rows
