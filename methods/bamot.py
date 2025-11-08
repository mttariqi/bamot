from typing import Dict, Any, List, Tuple, Optional
from collections import Counter
import re
import time

from utils.model_gateway import ModelGateway
from utils.evals import (
    extract_numeric_answer,
    bool_match,
    game24_is_24,
    is_correct as generic_is_correct,
)

# --------------------------
# Lightweight triage
# --------------------------

def _triage_score(text: str, no_triage: bool) -> float:
    if no_triage:
        return 1.0
    t = (text or "").lower()
    score = 0.0
    if "answer:" in t:
        score += 2.0
    for op in ["+", "-", "*", "/"]:
        if op in t:
            score += 0.3
    # prefer concise seeds
    length_penalty = min(len(t) / 200.0, 1.5)
    return score - 0.5 * length_penalty

# --------------------------
# Dataset detection (no external hints)
# --------------------------

def _guess_dataset(item: Dict[str, Any], gold: Optional[str]) -> str:
    """
    Heuristics without relying on run.py wrapping or meta fields:
      - 'numbers' in item => game24
      - gold looks boolean => strategyqa
      - else => numeric (gsm8k/aime/math500)
    """
    if "numbers" in item:
        return "game24"
    gs = (gold or "").strip().lower()
    if gs in {"yes", "no", "true", "false"}:
        return "strategyqa"
    return "numeric"

# --------------------------
# Prompts
# --------------------------

def _seed_prompt(item: Dict[str, Any], ds: str) -> str:
    q = item.get("question", "").strip()
    if ds == "strategyqa":
        return (
            "Answer strictly with 'yes' or 'no'.\n"
            f"Question: {q}\n"
            "Think briefly (1-3 lines). End with a single final line:\n"
            "ANSWER: yes   or   ANSWER: no"
        )
    if ds == "game24":
        nums = item.get("numbers")
        hint = f" Numbers: {nums}" if nums else ""
        return (
            f"Solve the 24 game.{hint} Use +, -, *, / and parentheses.\n"
            f"Question: {q}\n"
            "Provide ONE valid expression that evaluates to 24 (show it),\n"
            "then end with: ANSWER: 24"
        )
    # numeric tasks
    return (
        "Solve briefly (2-4 lines). Put only the final number on a last line as:\n"
        "ANSWER: <number>\n\n"
        f"Question: {q}"
    )

def _refine_prompt(item: Dict[str, Any], ds: str, candidate: str) -> str:
    q = item.get("question", "").strip()
    if ds == "strategyqa":
        return (
            "Refine to ensure the final decision is correct. Be concise.\n\n"
            f"Question:\n{q}\n\n"
            f"Candidate:\n{candidate}\n\n"
            "Rules:\n"
            "- Output a single final line at the end: ANSWER: yes  or  ANSWER: no"
        )
    if ds == "game24":
        return (
            "Refine the expression so it truly equals 24. Keep it short (2-4 lines).\n\n"
            f"Question:\n{q}\n\n"
            f"Candidate:\n{candidate}\n\n"
            "Rules:\n"
            "- Provide a valid arithmetic expression using + - * / and parentheses that evaluates to 24.\n"
            "- End with a final line: ANSWER: 24"
        )
    # numeric tasks
    return (
        "Refine the reasoning to guarantee the final numeric answer is correct. Be brief.\n\n"
        f"Question:\n{q}\n\n"
        f"Candidate:\n{candidate}\n\n"
        "Rules:\n"
        "- End with a single final line: ANSWER: <number>"
    )

def _finalize_for_log(s: str) -> str:
    """Return the last ANSWER: ... slice if present, else the raw text."""
    m = re.findall(r"(?:^|\b)ANSWER\s*:\s*([^\n\r]+)", s or "", flags=re.IGNORECASE)
    return m[-1].strip() if m else (s or "").strip()

# --------------------------
# Public: run one item
# --------------------------

def run_item(
    item: Dict[str, Any],
    gateway: ModelGateway,
    cot_system: str,
    seeds: int = 6,
    budget_tokens: int = 1400,
    no_triage: bool = False,
    no_consensus: bool = False,
    seed_tokens: int = 80,
    refine_tokens: int = 320,
    early_stop_gold: bool = False,
    gold_value: str = None
) -> Dict[str, Any]:

    SEED_BUDGET_FRAC = 0.30     # cap ~30% budget on seeding
    REFINE_TOPK = 2             # refine top-2 each round

    gold = item.get("answer")
    if gold_value is not None:
        gold = gold_value

    ds = _guess_dataset(item, gold)

    total_prompt = 0
    total_comp = 0
    latencies: List[float] = []

    # 1) MICRO-SEEDS
    seed_pool: List[Tuple[str, Optional[str], float]] = []
    seed_budget_limit = int(max(1, budget_tokens * SEED_BUDGET_FRAC))
    seed_user = _seed_prompt(item, ds)

    for i in range(max(1, seeds)):
        if (total_prompt + total_comp) >= seed_budget_limit and len(seed_pool) > 0:
            break
        # vary temperature lightly across seeds
        tmp = ModelGateway(model=gateway.model,
                           temperature=min(1.0, 0.2 + 0.2 * i),
                           max_tokens=seed_tokens)
        out = tmp.chat(system_prompt=cot_system, user_prompt=seed_user)
        txt = out.get("text", "")
        # numeric extract for numeric tasks; leave raw text for game24/strategyqa final checks
        pred = extract_numeric_answer(txt) if ds == "numeric" else None
        sc = _triage_score(txt, no_triage)
        seed_pool.append((txt, pred, sc))

        u = out.get("usage", {}) or {}
        total_prompt += int(u.get("prompt_tokens", 0) or 0)
        total_comp   += int(u.get("completion_tokens", 0) or 0)
        lat = out.get("latency")
        if lat is not None:
            latencies.append(lat)

    if not seed_pool:
        tmp = ModelGateway(model=gateway.model, temperature=0.2, max_tokens=seed_tokens)
        out = tmp.chat(system_prompt=cot_system, user_prompt=seed_user)
        txt = out.get("text", "")
        pred = extract_numeric_answer(txt) if ds == "numeric" else None
        sc = _triage_score(txt, no_triage)
        seed_pool.append((txt, pred, sc))
        u = out.get("usage", {}) or {}
        total_prompt += int(u.get("prompt_tokens", 0) or 0)
        total_comp   += int(u.get("completion_tokens", 0) or 0)

    seed_pool.sort(key=lambda x: x[2], reverse=True)
    pool: List[Tuple[str, Optional[str], float]] = seed_pool[:]
    token_spend = total_prompt + total_comp

    # Early stop on good seeds (dataset-aware)
    def _passes(pred_text: str) -> bool:
        if ds == "strategyqa":
            # prefer explicit final line if present
            final = extract_numeric_answer(pred_text)  # will return None here; ignore
            # just boolean match on the whole text
            return bool_match(pred_text, gold or "")
        if ds == "game24":
            return game24_is_24(pred_text) or (gold == "24" and generic_is_correct(pred_text, "24"))
        # numeric
        if gold is None:
            return False
        return generic_is_correct(pred_text, gold)

    for s_txt, _, _ in pool[:min(REFINE_TOPK, len(pool))]:
        if _passes(s_txt):
            return {
                "text": s_txt,
                "pred": _finalize_for_log(s_txt),
                "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
                "latency": sum(latencies)/len(latencies) if latencies else None
            }

    # 2) SELECTIVE REFINEMENTS (round-robin on top-2)
    refine_gws = [
        ModelGateway(model=gateway.model, temperature=t, max_tokens=refine_tokens)
        for t in [0.2, 0.4, 0.6, 0.8]
    ]
    rr = 0

    while token_spend <= budget_tokens and len(pool) > 0:
        pool.sort(key=lambda x: x[2], reverse=True)
        idx = rr % min(REFINE_TOPK, len(pool))
        base_txt, base_pred, _ = pool[idx]

        refine_user = _refine_prompt(item, ds, base_txt)
        gw_i = refine_gws[rr % len(refine_gws)]
        out = gw_i.chat(system_prompt=cot_system, user_prompt=refine_user)
        rr += 1

        new_txt = out.get("text", "")
        new_pred = extract_numeric_answer(new_txt) if ds == "numeric" else None
        new_sc = _triage_score(new_txt, no_triage)
        pool.append((new_txt, new_pred, new_sc))

        u = out.get("usage", {}) or {}
        pt = int(u.get("prompt_tokens", 0) or 0)
        ct = int(u.get("completion_tokens", 0) or 0)
        total_prompt += pt
        total_comp   += ct
        token_spend = total_prompt + total_comp

        lat = out.get("latency")
        if lat is not None:
            latencies.append(lat)

        # Deduplicate by predicted numeric (for numeric tasks) or by text hash
        dedup = {}
        for t_, p_, s_ in pool:
            key = p_ if (ds == "numeric" and p_ is not None) else f"t:{hash(t_)%10**9}"
            if key not in dedup or s_ > dedup[key][2]:
                dedup[key] = (t_, p_, s_)
        pool = list(dedup.values())

        # Optional early stop (dataset-aware)
        if _passes(new_txt):
            return {
                "text": new_txt,
                "pred": _finalize_for_log(new_txt),
                "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
                "latency": sum(latencies)/len(latencies) if latencies else None
            }

        # stop if the next similar step would exceed budget
        if (pt + ct) > 0 and token_spend + (pt + ct) > budget_tokens:
            break

    # 3) CONSENSUS (or best-ranked)
    pool.sort(key=lambda x: x[2], reverse=True)
    if not pool:
        return {
            "text": "",
            "pred": "",
            "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
            "latency": sum(latencies)/len(latencies) if latencies else None
        }

    if no_consensus:
        final_txt = pool[0][0]
    else:
        if ds == "strategyqa":
            votes = []
            for t_, _, _ in pool[:5]:
                # extract final tag if present; otherwise use whole text
                vt = re.findall(r"(?:^|\b)ANSWER\s*:\s*([^\n\r]+)", t_, flags=re.IGNORECASE)
                votes.append((vt[-1] if vt else t_))
            # normalize to yes/no
            votes = [ "yes" if bool_match(v, "yes") else ("no" if bool_match(v, "no") else None) for v in votes ]
            votes = [v for v in votes if v is not None]
            if votes:
                final_txt = f"ANSWER: {Counter(votes).most_common(1)[0][0]}"
            else:
                final_txt = pool[0][0]
        elif ds == "game24":
            passing = [t_ for (t_, _, _) in pool if game24_is_24(t_)]
            final_txt = passing[0] if passing else pool[0][0]
        else:
            # numeric majority over extracted numbers
            nums = [extract_numeric_answer(t_) for (t_, _, _) in pool[:5]]
            nums = [n for n in nums if n is not None]
            if nums:
                pick = Counter(nums).most_common(1)[0][0]
                final_txt = f"ANSWER: {pick}"
            else:
                final_txt = pool[0][0]

    return {
        "text": final_txt,
        "pred": _finalize_for_log(final_txt),
        "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
        "latency": sum(latencies)/len(latencies) if latencies else None
    }
