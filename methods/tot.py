from typing import Dict, Any, List, Tuple, Optional
import math

from utils.model_gateway import ModelGateway
from utils.evals import (
    extract_numeric_answer,
    is_game24_correct,
    extract_game24_expression,
    _numbers_from_question,
    _safe_eval,
)
from utils.tokens import estimate_tokens

def score_partial(text: str, task_mode: str = "numeric", target_nums: Optional[List[int]] = None) -> float:
    """Improved scoring for different task types."""
    if task_mode == "game24":
        from methods.bamot import _extract_all_game24_exprs
        from collections import Counter
        from utils.evals import _nums_from_str
        
        def _uses_exact_multiset(expr: str, target_nums: List[int]) -> bool:
            used = Counter(_nums_from_str(expr))
            want = Counter(target_nums)
            return used == want
        
        exprs = _extract_all_game24_exprs(text)
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
        has_ans = 1.0 if "ANSWER:" in text else 0.0
        has_num = 1.0 if any(ch.isdigit() for ch in text) else 0.0
        return 0.6*has_ans + 0.4*has_num

def expand(
    gateway: ModelGateway,
    system: str,
    question: str,
    prefix: str,
    k: int = 3,
    task_mode: str = "numeric",
    target_nums: Optional[List[int]] = None,
    *,
    request_chat,
):
    outs = []
    for i in range(k):
        if task_mode == "game24":
            prompt = (
                f"{question}\n\nTry a different approach ({i+1}/{k}). Use ONLY {target_nums} exactly once each.\n"
                f"Current attempt:\n{prefix}\n\nReturn: EXPR: <expression>  ANSWER: 24"
            )
        else:
            prompt = (
                f"{question}\n\nContinue reasoning from this partial attempt and try an alternative path ({i+1}/{k}). "
                f"End with: ANSWER: <number>\n\nPartial attempt:\n{prefix}"
            )
        out = request_chat(prompt)
        if out is None:
            break
        outs.append(out)
    return outs

def run_item(
    item: Dict[str, Any],
    gateway: ModelGateway,
    cot_system: str,
    branch: int = 3,
    depth: int = 2,
    token_budget: Optional[int] = None,
):
    question = item.get("question", "")
    task_mode = "game24" if ("make 24" in question.lower() or "to make 24" in question.lower()) else "numeric"
    target_nums = None
    if task_mode == "game24":
        target_nums = item.get("numbers")
        if not target_nums:
            target_nums = _numbers_from_question(question)
    
    # root expansion
    if task_mode == "game24":
        root_prompt = f"{question}\n\nUse ONLY the numbers {target_nums} exactly once each with + - * / and parentheses to make 24.\nReturn: EXPR: <expression>  ANSWER: 24"
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
        lat = out.get("latency", None)
        if lat is not None:
            latencies.append(lat)
        return out

    root_out = request_chat(root_prompt)
    if root_out is None:
        return {"text": "BUDGET_EXHAUSTED", "pred": None, "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp}, "latency": None}

    pool: List[Tuple[str, float]] = [(root_out["text"], score_partial(root_out["text"], task_mode, target_nums))]

    # breadth-first up to depth
    frontier = [root_out["text"]]
    for d in range(depth):
        rem = remaining_budget()
        if rem is not None and rem <= safety_margin:
            break
        next_frontier = []
        candidates = []
        for partial in frontier:
            rem = remaining_budget()
            if rem is not None and rem <= safety_margin:
                break
            outs = expand(
                gateway,
                cot_system,
                question,
                partial,
                k=branch,
                task_mode=task_mode,
                target_nums=target_nums,
                request_chat=request_chat,
            )
            for o in outs:
                txt = o["text"]
                sc = score_partial(txt, task_mode, target_nums)
                candidates.append((txt, sc))
                rem = remaining_budget()
                if rem is not None and rem <= safety_margin:
                    break
        # select top 'branch' for next level
        candidates.sort(key=lambda x: x[1], reverse=True)
        frontier = [c[0] for c in candidates[:branch]]
        pool.extend(candidates[:branch])

    # choose best leaf by score
    pool.sort(key=lambda x: x[1], reverse=True)
    best_txt = pool[0][0]
    
    if task_mode == "game24":
        pred = extract_game24_expression(best_txt)
    else:
        pred = extract_numeric_answer(best_txt)
    
    avg_latency = sum(latencies)/len(latencies) if latencies else None
    return {"text": best_txt, "pred": pred, "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp}, "latency": avg_latency}
