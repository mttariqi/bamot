from typing import Dict, Any, List, Tuple
from collections import Counter
from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer

def _triage_score(text: str, no_triage: bool) -> float:
    if no_triage:
        return 1.0
    has_ans = 1.0 if "ANSWER:" in text else 0.0
    has_num = 1.0 if any(ch.isdigit() for ch in text) else 0.0
    length_penalty = max(0.0, 1.0 - (len(text) / 400.0))  # prefer concise
    return 0.5*has_ans + 0.3*has_num + 0.2*length_penalty

def run_item(item: Dict[str, Any], gateway: ModelGateway, cot_system: str,
             seeds: int = 6, budget_tokens: int = 1400,
             no_triage: bool = False, no_consensus: bool = False,
             seed_tokens: int = 80, refine_tokens: int = 320,
             early_stop_gold: bool = False, gold_value: str = None) -> Dict[str, Any]:
    """
    BAMoT (budget-aware):
      (1) Micro-seeds generated UNTIL a fraction of the total budget is used (to avoid overspending on seeding)
      (2) Selective refinements over top-2 candidates (round-robin)
      (3) Consensus (or best) at the end
      (4) Optional early stop if predicted equals known gold (e.g., '24')
    """
    SEED_BUDGET_FRAC = 0.30       # <= 30% of total budget on seeding (was 0.50)
    REFINE_TOPK = 2               # refine two best candidates in round-robin

    total_prompt = 0
    total_comp = 0
    latencies: List[float] = []

    question = item['question']
    gold = item.get("answer")
    target = gold_value if gold_value is not None else gold

    # ---------- 1) MICRO-SEEDS (budget-aware) ----------
    seed_pool: List[Tuple[str, str, float]] = []
    seed_budget_limit = int(max(1, budget_tokens * SEED_BUDGET_FRAC))

    for i in range(seeds):
        if (total_prompt + total_comp) >= seed_budget_limit and len(seed_pool) > 0:
            break

        tmp = ModelGateway(model=gateway.model,
                           temperature=min(1.0, 0.2 + 0.2*i),
                           max_tokens=seed_tokens)
        prompt = f"{question}\n\nGive a brief plan and a tentative numeric result. End with: ANSWER: <number>"
        out = tmp.chat(system_prompt=cot_system, user_prompt=prompt)

        txt = out["text"]
        pred = extract_numeric_answer(txt)
        sc = _triage_score(txt, no_triage)
        seed_pool.append((txt, pred, sc))

        u = out.get("usage", {}) or {}
        total_prompt += u.get("prompt_tokens", 0) or 0
        total_comp   += u.get("completion_tokens", 0) or 0
        lat = out.get("latency", None)
        if lat is not None:
            latencies.append(lat)

    # ensure at least one seed
    if not seed_pool:
        tmp = ModelGateway(model=gateway.model, temperature=0.2, max_tokens=seed_tokens)
        prompt = f"{question}\n\nGive a brief plan and a tentative numeric result. End with: ANSWER: <number>"
        out = tmp.chat(system_prompt=cot_system, user_prompt=prompt)
        txt = out["text"]; pred = extract_numeric_answer(txt); sc = _triage_score(txt, no_triage)
        seed_pool.append((txt, pred, sc))
        u = out.get("usage", {}) or {}
        total_prompt += u.get("prompt_tokens", 0) or 0
        total_comp   += u.get("completion_tokens", 0) or 0

    seed_pool.sort(key=lambda x: x[2], reverse=True)
    best_pool: List[Tuple[str, str, float]] = seed_pool[:]
    token_spend = total_prompt + total_comp

    # Early stop if a seed already matches gold
    if early_stop_gold and target is not None:
        for _, p, _ in best_pool[:REFINE_TOPK]:
            if p is not None and str(p).strip() == str(target).strip():
                trace = "\n\n==== MICRO-SEEDS (EARLY STOP) ====\n\n" + "\n\n----\n\n".join([c[0] for c in best_pool[:3]])
                return {"text": trace,
                        "pred": str(target),
                        "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
                        "latency": sum(latencies)/len(latencies) if latencies else None}

    # ---------- 2) SELECTIVE REFINEMENTS (round-robin top-2) ----------
    refine_gws = [
        ModelGateway(model=gateway.model, temperature=t, max_tokens=refine_tokens)
        for t in [0.2, 0.4, 0.6, 0.8]
    ]
    rr = 0  # round-robin index

    while token_spend <= budget_tokens:
        best_pool.sort(key=lambda x: x[2], reverse=True)
        idx = rr % min(REFINE_TOPK, len(best_pool))
        base_txt, base_pred, _ = best_pool[idx]

        refine_prompt = (
            f"Refine and verify the final numeric result.\n\n"
            f"Question:\n{question}\n\n"
            f"Current attempt:\n{base_txt}\n\n"
            f"If a correction is needed, fix it. End with: ANSWER: <number>"
        )
        gw_i = refine_gws[rr % len(refine_gws)]
        out = gw_i.chat(system_prompt=cot_system, user_prompt=refine_prompt)
        rr += 1

        new_txt = out["text"]
        new_pred = extract_numeric_answer(new_txt)
        new_sc = _triage_score(new_txt, no_triage)
        best_pool.append((new_txt, new_pred, new_sc))

        u = out.get("usage", {}) or {}
        pt = u.get("prompt_tokens", 0) or 0
        ct = u.get("completion_tokens", 0) or 0
        total_prompt += pt
        total_comp += ct
        token_spend = total_prompt + total_comp

        lat = out.get("latency", None)
        if lat is not None:
            latencies.append(lat)

        # merge-equivalent by predicted answer
        dedup = {}
        for t_, p_, s_ in best_pool:
            key = p_ if p_ is not None else f"_{hash(t_)%10**8}"
            if key not in dedup or s_ > dedup[key][2]:
                dedup[key] = (t_, p_, s_)
        best_pool = list(dedup.values())

        # Optional early stop once the top candidate hits the gold value
        if early_stop_gold and target is not None:
            bp0 = best_pool[0][1]
            if bp0 is not None and str(bp0).strip() == str(target).strip():
                break

        # stop if next similar step would exceed budget
        if (pt + ct) > 0 and token_spend + (pt + ct) > budget_tokens:
            break

    # ---------- 3) CONSENSUS (or best) ----------
    best_pool.sort(key=lambda x: x[2], reverse=True)
    if no_consensus:
        final_pred = best_pool[0][1]
    else:
        top_preds = [p for (_, p, _) in best_pool[:3] if p is not None]
        final_pred = Counter(top_preds).most_common(1)[0][0] if top_preds else None

    trace = "\n\n==== TOP CANDIDATES ====\n\n" + "\n\n----\n\n".join([c[0] for c in best_pool[:3]])
    avg_latency = sum(latencies)/len(latencies) if latencies else None
    return {"text": trace,
            "pred": final_pred,
            "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
            "latency": avg_latency}
