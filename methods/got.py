from typing import Dict, Any, List, Tuple
from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer

def _score(txt: str) -> float:
    has = 1.0 if "ANSWER:" in txt else 0.0
    num = 1.0 if any(ch.isdigit() for ch in txt) else 0.0
    return 0.6*has + 0.4*num

def run_item(item: Dict[str, Any], gateway: ModelGateway, cot_system: str, steps: int = 3, beam: int = 4):
    prompt = f"{item['question']}\n\nShow your work. End with: ANSWER: <number>"
    root = gateway.chat(system_prompt=cot_system, user_prompt=prompt)

    total_prompt = (root.get("usage", {}) or {}).get("prompt_tokens", 0) or 0
    total_comp   = (root.get("usage", {}) or {}).get("completion_tokens", 0) or 0

    pool: List[Tuple[str, str, float]] = [(root['text'], extract_numeric_answer(root['text']), _score(root['text']))]

    for _ in range(steps):
        pool.sort(key=lambda x: x[2], reverse=True)
        frontier = pool[:beam]
        new_nodes: List[Tuple[str, str, float]] = []
        for (txt, pred, sc) in frontier:
            rp = f"Consider an alternative path but reuse any valid partial results.\n\nQuestion: {item['question']}\n\nCurrent:\n{txt}\n\nEnd with: ANSWER: <number>"
            out = gateway.chat(system_prompt=cot_system, user_prompt=rp)
            t = out["text"]
            p = extract_numeric_answer(t)
            s = _score(t)
            new_nodes.append((t,p,s))
            u = out.get("usage", {}) or {}
            total_prompt += u.get("prompt_tokens", 0) or 0
            total_comp   += u.get("completion_tokens", 0) or 0

        # merge by predicted answer
        merged = {}
        for t,p,s in pool + new_nodes:
            key = p if p is not None else t[-120:]
            if key not in merged or s > merged[key][2]:
                merged[key] = (t,p,s)
        pool = list(merged.values())

    pool.sort(key=lambda x: x[2], reverse=True)
    best_txt, best_pred, _ = pool[0]
    return {"text": best_txt, "pred": best_pred, "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp}}
