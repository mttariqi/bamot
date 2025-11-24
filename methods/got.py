from typing import Dict, Any, List, Tuple, Optional
import math
from collections import Counter

from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer, extract_game24_expression, _numbers_from_question, _safe_eval
from utils.tokens import estimate_tokens

def _score(txt: str, task_mode: str = "numeric", target_nums: Optional[List[int]] = None) -> float:
    """Improved scoring for Graph-of-Thoughts."""
    if task_mode == "game24":
        from methods.bamot import _extract_all_game24_exprs
        from utils.evals import _nums_from_str
        
        def _uses_exact_multiset(expr: str, target_nums: List[int]) -> bool:
            used = Counter(_nums_from_str(expr))
            want = Counter(target_nums)
            return used == want
        
        exprs = _extract_all_game24_exprs(txt)
        best = 0.0
        for e in exprs[:3]:
            val = _safe_eval(e)
            if val is not None:
                close = 1.0 / (1.0 + abs(val - 24.0))
                nums_ok = 1.0 if (target_nums and _uses_exact_multiset(e, target_nums)) else 0.0
                if math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9) and nums_ok:
                    return 1.0
                best = max(best, 0.7 * close + 0.3 * nums_ok)
        return best if best > 0 else 0.1
    else:
        has = 1.0 if "ANSWER:" in txt else 0.0
        num = 1.0 if any(ch.isdigit() for ch in txt) else 0.0
        return 0.6*has + 0.4*num

def run_item(
    item: Dict[str, Any],
    gateway: ModelGateway,
    cot_system: str,
    steps: int = 3,
    beam: int = 4,
    token_budget: Optional[int] = None,
):
    question = item.get("question", "")
    task_mode = "game24" if ("make 24" in question.lower() or "to make 24" in question.lower()) else "numeric"
    target_nums = None
    if task_mode == "game24":
        target_nums = item.get("numbers")
        if not target_nums:
            target_nums = _numbers_from_question(question)
    
    if task_mode == "game24":
        root_prompt = (
            f"{question}\n\nUse ONLY the numbers {target_nums} exactly once each with + - * / and parentheses to make 24.\n"
            "Return: EXPR: <expression>  ANSWER: 24"
        )
    else:
        root_prompt = f"{question}\n\nShow your work. End with: ANSWER: <number>"
    
    total_prompt = 0
    total_comp = 0
    latencies: List[float] = []
    safety_margin = 32

    def remaining_budget():
        if token_budget is None:
            return None
        return token_budget - (total_prompt + total_comp)

    def request_chat(user_prompt: str):
        nonlocal total_prompt, total_comp
        max_override = None
        if token_budget is not None:
            rem = remaining_budget()
            if rem is None or rem <= safety_margin:
                return None
            prompt_est = estimate_tokens(cot_system) + estimate_tokens(user_prompt)
            if rem <= prompt_est + safety_margin:
                return None
            available = rem - prompt_est - safety_margin
            if available < 16:
                return None
            max_override = min(gateway.max_tokens, int(available))
        out = gateway.chat(
            system_prompt=cot_system,
            user_prompt=user_prompt,
            max_tokens_override=max_override,
        )
        usage = out.get("usage", {}) or {}
        total_prompt += usage.get("prompt_tokens", 0) or 0
        total_comp += usage.get("completion_tokens", 0) or 0
        lat = out.get("latency")
        if lat:
            latencies.append(lat)
        return out

    root = request_chat(root_prompt)
    if root is None:
        return {
            "text": "BUDGET_EXHAUSTED",
            "pred": None,
            "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
            "latency": None,
        }

    pool: List[Tuple[str, str, float]] = [
        (root['text'], 
         extract_game24_expression(root['text']) if task_mode == "game24" else extract_numeric_answer(root['text']), 
         _score(root['text'], task_mode, target_nums))
    ]

    for _ in range(steps):
        rem = remaining_budget()
        if rem is not None and rem <= safety_margin:
            break
        pool.sort(key=lambda x: x[2], reverse=True)
        frontier = pool[:beam]
        new_nodes: List[Tuple[str, str, float]] = []
        for (txt, pred, sc) in frontier:
            rem = remaining_budget()
            if rem is not None and rem <= safety_margin:
                break
            if task_mode == "game24":
                rp = (
                    f"Consider an alternative approach. Use ONLY {target_nums} exactly once each.\n\n"
                    f"Question: {question}\n\nCurrent:\n{txt}\n\nReturn: EXPR: <expression>  ANSWER: 24"
                )
            else:
                rp = (
                    f"Consider an alternative path but reuse any valid partial results.\n\nQuestion: {question}\n\nCurrent:\n{txt}\n\n"
                    "End with: ANSWER: <number>"
                )
            out = request_chat(rp)
            if out is None:
                break
            t = out["text"]
            p = extract_game24_expression(t) if task_mode == "game24" else extract_numeric_answer(t)
            s = _score(t, task_mode, target_nums)
            new_nodes.append((t,p,s))
            rem = remaining_budget()
            if rem is not None and rem <= safety_margin:
                break

        # merge by predicted answer (GoT key feature: merging nodes)
        merged = {}
        for t,p,s in pool + new_nodes:
            key = p if p is not None else t[-120:]
            if key not in merged or s > merged[key][2]:
                merged[key] = (t,p,s)
        pool = list(merged.values())

    pool.sort(key=lambda x: x[2], reverse=True)
    best_txt, best_pred, _ = pool[0]
    avg_latency = sum(latencies)/len(latencies) if latencies else None
    return {
        "text": best_txt, 
        "pred": best_pred, 
        "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
        "latency": avg_latency
    }
