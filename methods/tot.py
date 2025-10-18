from typing import Dict, Any, List, Tuple
from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer

def score_partial(text: str) -> float:
    has_ans = 1.0 if "ANSWER:" in text else 0.0
    has_num = 1.0 if any(ch.isdigit() for ch in text) else 0.0
    return 0.6*has_ans + 0.4*has_num

def expand(gateway: ModelGateway, system: str, question: str, prefix: str, k: int = 3):
    outs = []
    for i in range(k):
        prompt = f"{question}\n\nContinue reasoning from this partial attempt and try an alternative path ({i+1}/{k}). End with: ANSWER: <number>\n\nPartial attempt:\n{prefix}"
        out = gateway.chat(system_prompt=system, user_prompt=prompt)
        outs.append(out)
    return outs

def run_item(item: Dict[str, Any], gateway: ModelGateway, cot_system: str, branch: int = 3, depth: int = 2):
    # root expansion
    root_prompt = f"{item['question']}\n\nShow your work. End with: ANSWER: <number>"
    root_out = gateway.chat(system_prompt=cot_system, user_prompt=root_prompt)
    usage_root = root_out.get("usage", {})
    lat_root = root_out.get("latency", None)
    pool: List[Tuple[str, float]] = [(root_out["text"], score_partial(root_out["text"]))]

    total_prompt = usage_root.get("prompt_tokens", 0) or 0
    total_comp   = usage_root.get("completion_tokens", 0) or 0
    latencies = [lat_root] if lat_root is not None else []

    # breadth-first up to depth
    frontier = [root_out["text"]]
    for d in range(depth):
        next_frontier = []
        candidates = []
        for partial in frontier:
            outs = expand(gateway, cot_system, item['question'], partial, k=branch)
            for o in outs:
                txt = o["text"]
                sc = score_partial(txt)
                candidates.append((txt, sc))
                usage = o.get("usage", {})
                total_prompt += usage.get("prompt_tokens", 0) or 0
                total_comp   += usage.get("completion_tokens", 0) or 0
                lat = o.get("latency", None)
                if lat is not None:
                    latencies.append(lat)
        # select top 'branch' for next level
        candidates.sort(key=lambda x: x[1], reverse=True)
        frontier = [c[0] for c in candidates[:branch]]
        pool.extend(candidates[:branch])

    # choose best leaf by score
    pool.sort(key=lambda x: x[1], reverse=True)
    best_txt = pool[0][0]
    pred = extract_numeric_answer(best_txt)
    avg_latency = sum(latencies)/len(latencies) if latencies else None
    return {"text": best_txt, "pred": pred, "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp}, "latency": avg_latency}
