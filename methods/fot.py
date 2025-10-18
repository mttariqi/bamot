from typing import Dict, Any, List
from collections import Counter
from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer

def run_item(item: Dict[str, Any], gateway: ModelGateway, cot_system: str,
             trees: int = 3, branch: int = 1, depth: int = 1):
    def score(txt: str) -> float:
        has = 1.0 if "ANSWER:" in txt else 0.0
        num = 1.0 if any(ch.isdigit() for ch in txt) else 0.0
        return 0.6*has + 0.4*num

    def run_tree(tmp_gw: ModelGateway, q: str, system: str):
        total_prompt = 0
        total_comp = 0
        # root
        root = tmp_gw.chat(system_prompt=system, user_prompt=f"{q}\n\nShow your work. End with: ANSWER: <number>")
        pool = [root["text"]]
        u = root.get("usage", {}) or {}
        total_prompt += u.get("prompt_tokens", 0) or 0
        total_comp   += u.get("completion_tokens", 0) or 0

        # shallow branches
        for _ in range(depth):
            new = []
            for p in pool:
                for _ in range(branch):
                    out = tmp_gw.chat(
                        system_prompt=system,
                        user_prompt=f"{q}\n\nTry a distinct reasoning branch.\nCurrent:\n{p}\n\nEnd with: ANSWER: <number>"
                    )
                    new.append(out["text"])
                    u = out.get("usage", {}) or {}
                    total_prompt += u.get("prompt_tokens", 0) or 0
                    total_comp   += u.get("completion_tokens", 0) or 0
            pool = sorted(new, key=score, reverse=True)[:max(1, branch)]
        best = sorted(pool, key=score, reverse=True)[0]
        return best, total_prompt, total_comp

    preds: List[str] = []
    tot_prompt = 0
    tot_comp = 0
    for i in range(trees):
        tmp = ModelGateway(model=gateway.model, temperature=min(1.0, 0.2 + 0.2*i), max_tokens=gateway.max_tokens)
        best_txt, pt, ct = run_tree(tmp, item['question'], cot_system)
        preds.append(extract_numeric_answer(best_txt))
        tot_prompt += pt
        tot_comp   += ct

    preds = [p for p in preds if p is not None]
    final = Counter(preds).most_common(1)
    pred = final[0][0] if final else None
    return {"text": "FoT preds=" + ",".join(preds),
            "pred": pred,
            "usage": {"prompt_tokens": tot_prompt, "completion_tokens": tot_comp}}
