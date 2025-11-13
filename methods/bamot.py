# methods/bamot.py
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter
import math, re

from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer, extract_game24_expression, is_game24_correct

def _detect_task_mode(question: str) -> str:
    q = (question or "").lower()
    if "make 24" in q or "to make 24" in q: return "game24"
    if "single word: yes or no" in q:       return "boolean"
    return "numeric"

def _seed_tail(task_mode: str) -> str:
    if task_mode == "boolean":
        return "Answer strictly with a single word: yes or no."
    if task_mode == "game24":
        return ("Return ONE line only: a single arithmetic expression using the four given numbers "
                "exactly once with + - * / and parentheses. End with: ANSWER: 24")
    return "Give a brief plan and a tentative numeric result. End with: ANSWER: <number>"

def _refine_prompt(task_mode: str, question: str, attempt_text: str, feedback: str) -> str:
    if task_mode == "boolean":
        return ("Refine and verify the final decision. Return only 'yes' or 'no'.\n"
                f"Question: {question}\nCurrent attempt: {attempt_text}\nFeedback: {feedback}\nAnswer:")
    if task_mode == "game24":
        return ("Refine to ONE valid expression that equals 24 using each of the four numbers exactly once "
                "with + - * / and parentheses. No words. End with: ANSWER: 24\n"
                f"Question: {question}\nCurrent attempt: {attempt_text}\nFeedback: {feedback}\nExpression:")
    return ("Refine and verify the final numeric result.\n"
            f"Question: {question}\nCurrent attempt: {attempt_text}\nFeedback: {feedback}\n"
            "If a correction is needed, fix it. End with: ANSWER: <number>\nAnswer:")

def run_item(
    item: Dict[str, Any],
    gateway: ModelGateway,
    cot_system: str,
    *,
    seeds: int = 2,
    budget_tokens: int = 1200,
    no_triage: bool = False,
    no_consensus: bool = False,
    seed_tokens: int = 80,
    refine_tokens: int = 256,
    early_stop_gold: bool = False,
    gold_value: Optional[str] = None,
    refine_topk: int = 2,
    seed_budget_frac: float = 0.30,
    **kwargs
) -> Dict[str, Any]:

    question = item.get("question","")
    task_mode = _detect_task_mode(question)

    total_prompt = 0
    total_comp = 0
    latencies: List[float] = []

    # 1) Micro-seeds (budget-capped)
    seed_pool: List[Tuple[str, Optional[str], float]] = []
    seed_budget_limit = int(max(1, budget_tokens * seed_budget_frac))

    def _score_text(text: str) -> float:
        if not text: return 0.0
        if task_mode == "boolean":
            s = text.lower()
            return 1.0 if (("yes" in s) ^ ("no" in s)) else 0.2
        if task_mode == "game24":
            expr = extract_game24_expression(text) or ""
            if not expr: return 0.1
            # closeness to 24 (if evaluable)
            try:
                val = float(eval(expr, {"__builtins__": None}, {}))
                close = 1.0 / (1.0 + abs(val - 24.0))
            except Exception:
                close = 0.0
            return 0.7 * close + 0.3
        # numeric
        return 1.0 if extract_numeric_answer(text) else 0.2

    for i in range(seeds):
        if (total_prompt + total_comp) >= seed_budget_limit and len(seed_pool) > 0:
            break
        tmp = ModelGateway(model=gateway.model, temperature=min(1.0, 0.2 + 0.2*i), max_tokens=seed_tokens)
        out = tmp.chat(system_prompt=cot_system, user_prompt=f"{question}\n\n{_seed_tail(task_mode)}")
        txt = out["text"]
        pred = None
        if task_mode == "boolean":
            s = txt.lower(); pred = "yes" if ("yes" in s and "no" not in s) else ("no" if "no" in s else None)
        elif task_mode == "numeric":
            pred = extract_numeric_answer(txt)
        else:
            pred = extract_game24_expression(txt)
            # Early-pass if already valid
            if pred and is_game24_correct(txt, question):
                u = out.get("usage", {}) or {}
                return {"text": txt, "pred": pred,
                        "usage": {"prompt_tokens": u.get("prompt_tokens",0), "completion_tokens": u.get("completion_tokens",0)},
                        "latency": out.get("latency")}
        sc = 1.0 if no_triage else _score_text(txt)
        seed_pool.append((txt, pred, sc))
        u = out.get("usage", {}) or {}
        total_prompt += u.get("prompt_tokens",0) or 0
        total_comp   += u.get("completion_tokens",0) or 0
        if out.get("latency") is not None: latencies.append(out["latency"])

    if not seed_pool:
        # fallback one seed
        out = gateway.chat(system_prompt=cot_system, user_prompt=f"{question}\n\n{_seed_tail(task_mode)}")
        txt = out["text"]
        seed_pool.append((txt, extract_numeric_answer(txt) if task_mode=="numeric" else None, _score_text(txt)))
        u = out.get("usage", {}) or {}
        total_prompt += u.get("prompt_tokens",0) or 0
        total_comp   += u.get("completion_tokens",0) or 0

    best_pool = sorted(seed_pool, key=lambda x: x[2], reverse=True)
    token_spend = total_prompt + total_comp

    # 2) Selective refinements (round-robin over top-K)
    refine_gws = [ModelGateway(model=gateway.model, temperature=t, max_tokens=refine_tokens) for t in (0.2,0.4,0.6,0.8)]
    rr = 0

    def _feedback_for(text: str) -> str:
        if task_mode != "game24": return "Fix mistakes and finalize."
        expr = extract_game24_expression(text)
        if not expr: return "No valid arithmetic expression detected. Output one expression only."
        # lightweight feedback: we’ll let grader verify exact numbers/24
        return "Ensure it equals 24 and uses each of the four numbers exactly once. Only + - * / and parentheses."

    while token_spend <= budget_tokens:
        best_pool.sort(key=lambda x: x[2], reverse=True)
        idx = rr % min(max(1, refine_topk), len(best_pool))
        base_txt, _, _ = best_pool[idx]
        gw_i = refine_gws[rr % len(refine_gws)]
        out = gw_i.chat(system_prompt=cot_system, user_prompt=_refine_prompt(task_mode, question, base_txt, _feedback_for(base_txt)))
        rr += 1

        new_txt = out["text"]
        if task_mode == "game24" and is_game24_correct(new_txt, question):
            u = out.get("usage", {}) or {}
            total_prompt += u.get("prompt_tokens",0) or 0
            total_comp   += u.get("completion_tokens",0) or 0
            if out.get("latency") is not None: latencies.append(out["latency"])
            return {"text": new_txt, "pred": extract_game24_expression(new_txt),
                    "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
                    "latency": sum(latencies)/len(latencies) if latencies else None}

        if task_mode == "boolean":
            s = new_txt.lower()
            new_pred = "yes" if ("yes" in s and "no" not in s) else ("no" if "no" in s else None)
        elif task_mode == "numeric":
            new_pred = extract_numeric_answer(new_txt)
        else:
            new_pred = extract_game24_expression(new_txt)

        new_sc = 1.0 if no_triage else _score_text(new_txt)
        best_pool.append((new_txt, new_pred, new_sc))

        u = out.get("usage", {}) or {}
        pt, ct = u.get("prompt_tokens",0) or 0, u.get("completion_tokens",0) or 0
        total_prompt += pt; total_comp += ct; token_spend = total_prompt + total_comp
        if out.get("latency") is not None: latencies.append(out["latency"])

        # dedup by surface (pred if present, else text)
        dedup = {}
        for t_, p_, s_ in best_pool:
            key = (p_ or t_)[:256]
            if key not in dedup or s_ > dedup[key][2]:
                dedup[key] = (t_, p_, s_)
        best_pool = list(dedup.values())

        if (pt + ct) > 0 and token_spend + (pt + ct) > budget_tokens:
            break

    # 3) Consensus / best
    best_pool.sort(key=lambda x: x[2], reverse=True)
    final_pred = best_pool[0][1]
    return {
        "text": best_pool[0][0],
        "pred": final_pred,
        "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
        "latency": (sum(latencies)/len(latencies)) if latencies else None,
    }
