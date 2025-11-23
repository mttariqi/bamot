from typing import Dict, Any, List, Tuple, Optional
from collections import Counter
import time
from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer, is_game24_correct, extract_game24_expression, _numbers_from_question, _safe_eval
from utils.tokens import estimate_tokens
import math

def score_partial(text: str, task_mode: str = "numeric", target_nums: Optional[List[int]] = None) -> float:
    """Improved scoring based on task type."""
    if task_mode == "game24":
        exprs = []
        # Try to extract expressions
        if "EXPR:" in text:
            parts = text.split("EXPR:")
            if len(parts) > 1:
                expr_part = parts[1].split("ANSWER:")[0].strip()
                exprs.append(expr_part)
        # Also try general extraction
        from methods.bamot import _extract_all_game24_exprs
        exprs.extend(_extract_all_game24_exprs(text))
        
        best = 0.0
        for e in exprs[:3]:  # Check top 3
            val = _safe_eval(e)
            if val is not None:
                close = 1.0 / (1.0 + abs(val - 24.0))
                nums_ok = 1.0 if (target_nums and _uses_exact_multiset(e, target_nums)) else 0.0
                if math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9) and nums_ok:
                    return 1.0  # Perfect
                best = max(best, 0.7 * close + 0.3 * nums_ok)
        return best if best > 0 else 0.1
    else:
        has_ans = 1.0 if "ANSWER:" in text else 0.0
        has_num = 1.0 if any(ch.isdigit() for ch in text) else 0.0
        return 0.6*has_ans + 0.4*has_num

def _uses_exact_multiset(expr: str, target_nums: List[int]) -> bool:
    from collections import Counter
    from utils.evals import _nums_from_str
    used = Counter(_nums_from_str(expr))
    want = Counter(target_nums)
    return used == want

def self_correct(
    chat_fn,
    question: str,
    current: str,
    task_mode: str,
    target_nums: Optional[List[int]] = None,
) -> Optional[Dict[str, Any]]:
    """Self-correction step from FoT paper."""
    if task_mode == "game24":
        feedback = "Review your expression. Ensure it uses the given numbers exactly once and evaluates to exactly 24."
        prompt = (
            f"{question}\n\nYour current attempt:\n{current}\n\n{feedback}\n\nRefine and correct. "
            "Return: EXPR: <expression>  ANSWER: 24"
        )
    else:
        feedback = "Review your reasoning. Check for calculation errors and logical mistakes."
        prompt = (
            f"{question}\n\nYour current attempt:\n{current}\n\n{feedback}\n\nRefine and correct. End with: ANSWER: <number>"
        )
    return chat_fn(prompt)

def run_tree(tmp_gw: ModelGateway, q: str, system: str, task_mode: str, target_nums: Optional[List[int]], 
             branch: int, depth: int, enable_correction: bool = True, token_budget: Optional[int] = None):
    """Run a single tree with optional self-correction."""
    total_prompt = 0
    total_comp = 0
    latencies = []

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
            prompt_est = estimate_tokens(system) + estimate_tokens(user_prompt)
            if rem <= prompt_est + safety_margin:
                return None
            available = rem - prompt_est - safety_margin
            if available < 16:
                return None
            max_override = min(tmp_gw.max_tokens, int(available))
        out = tmp_gw.chat(
            system_prompt=system,
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

    # Root node
    if task_mode == "game24":
        root_prompt = (
            f"{q}\n\nUse ONLY the numbers {target_nums} exactly once each with + - * / and parentheses to make 24.\n"
            "Return: EXPR: <expression>  ANSWER: 24"
        )
    else:
        root_prompt = f"{q}\n\nShow your work. End with: ANSWER: <number>"

    root = request_chat(root_prompt)
    if root is None:
        return "BUDGET_EXHAUSTED", total_prompt, total_comp, None
    pool = [root["text"]]

    # Expand tree
    for d in range(depth):
        rem = remaining_budget()
        if rem is not None and rem <= safety_margin:
            break
        new = []
        for p in pool:
            rem = remaining_budget()
            if rem is not None and rem <= safety_margin:
                break
            for b in range(branch):
                if task_mode == "game24":
                    expand_prompt = (
                        f"{q}\n\nTry a different approach. Use ONLY {target_nums} exactly once each.\n"
                        f"Current attempt:\n{p}\n\nReturn: EXPR: <expression>  ANSWER: 24"
                    )
                else:
                    expand_prompt = f"{q}\n\nTry an alternative reasoning path.\nCurrent:\n{p}\n\nEnd with: ANSWER: <number>"
                out = request_chat(expand_prompt)
                if out is None:
                    break
                new.append(out["text"])
                rem = remaining_budget()
                if rem is not None and rem <= safety_margin:
                    break
            rem = remaining_budget()
            if rem is not None and rem <= safety_margin:
                break
        
        # Self-correction on top candidates
        rem = remaining_budget()
        if enable_correction and new and (rem is None or rem > safety_margin):
            top_candidates = sorted(new, key=lambda x: score_partial(x, task_mode, target_nums), reverse=True)[:2]
            corrected = []
            for cand in top_candidates:
                corr_out = self_correct(request_chat, q, cand, task_mode, target_nums)
                if corr_out is None:
                    break
                corrected.append(corr_out["text"])
                rem = remaining_budget()
                if rem is not None and rem <= safety_margin:
                    break
            new.extend(corrected)
        
        # Select top branch candidates
        if new:
            pool = sorted(new, key=lambda x: score_partial(x, task_mode, target_nums), reverse=True)[:max(1, branch)]
        elif not pool:
            break
    
    if not pool:
        best = "BUDGET_EXHAUSTED"
    else:
        best = sorted(pool, key=lambda x: score_partial(x, task_mode, target_nums), reverse=True)[0]
    avg_latency = sum(latencies)/len(latencies) if latencies else None
    return best, total_prompt, total_comp, avg_latency

def run_item(item: Dict[str, Any], gateway: ModelGateway, cot_system: str,
             trees: int = 3, branch: int = 2, depth: int = 1, 
             enable_correction: bool = True, token_budget: Optional[int] = None):
    """Forest-of-Thoughts with self-correction and consensus."""
    question = item.get("question", "")
    
    # Detect task mode
    task_mode = "game24" if ("make 24" in question.lower() or "to make 24" in question.lower()) else "numeric"
    target_nums = None
    if task_mode == "game24":
        target_nums = item.get("numbers")
        if not target_nums:
            target_nums = _numbers_from_question(question)

    preds: List[str] = []
    all_texts: List[str] = []
    tot_prompt = 0
    tot_comp = 0
    all_latencies = []

    # Run multiple trees (forest)
    for i in range(trees):
        remaining_budget = None
        if token_budget is not None:
            remaining_budget = max(0, token_budget - (tot_prompt + tot_comp))
            if remaining_budget <= 0:
                break
        tmp = ModelGateway(
            model=gateway.model, 
            temperature=min(1.0, 0.2 + 0.2*i), 
            max_tokens=gateway.max_tokens,
            backend=gateway.backend,
            llama_model_path=gateway._llama_model_path,
            llama_ctx=gateway._llama_ctx,
            llama_threads=gateway._llama_threads
        )
        best_txt, pt, ct, lat = run_tree(
            tmp,
            question,
            cot_system,
            task_mode,
            target_nums,
            branch,
            depth,
            enable_correction,
            token_budget=remaining_budget,
        )
        all_texts.append(best_txt)
        
        # Extract prediction
        if task_mode == "game24":
            expr = extract_game24_expression(best_txt)
            if expr:
                preds.append(expr)
        else:
            pred = extract_numeric_answer(best_txt)
            if pred:
                preds.append(pred)
        
        tot_prompt += pt
        tot_comp += ct
        if lat:
            all_latencies.append(lat)

    # Consensus: majority voting
    if preds:
        final = Counter(preds).most_common(1)
        pred = final[0][0] if final else None
    else:
        pred = None
    
    avg_latency = sum(all_latencies)/len(all_latencies) if all_latencies else None
    
    return {
        "text": f"FoT: {len(preds)} predictions from {trees} trees",
        "pred": pred,
        "usage": {"prompt_tokens": tot_prompt, "completion_tokens": tot_comp},
        "latency": avg_latency
    }
