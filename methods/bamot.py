# methods/bamot.py
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter
import re, math

from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer

# --------------------------
# Lightweight Game-24 utils
# --------------------------

_ALLOWED_CHARS_RE = re.compile(r'^[\d\s\+\-\*/\(\)]+$')

def _safe_eval(expr: str) -> Optional[float]:
    if not expr or not _ALLOWED_CHARS_RE.match(expr):
        return None
    if "**" in expr or "//" in expr:
        return None
    try:
        return float(eval(expr, {"__builtins__": None}, {}))
    except Exception:
        return None

def _nums_from_str(s: str) -> List[int]:
    return [int(x) for x in re.findall(r'\b\d+\b', s or "")]

def _numbers_from_question(question: str) -> List[int]:
    # Typical: "Use 5, 5, 11, 12 with + - * / and parentheses to make 24."
    # Extract numbers, but filter out "24" that appears after "make 24" or "ANSWER: 24"
    # We want only the four input numbers, not the target 24
    nums = _nums_from_str(question)
    
    # Remove all instances of 24 that appear after "make 24" or similar phrases
    # Strategy: find the pattern "make 24" or "= 24" or "ANSWER: 24" and remove 24s after that
    question_lower = question.lower()
    make_24_pos = question_lower.find("make 24")
    answer_24_pos = question_lower.find("answer: 24")
    
    # Find the earliest position where "24" becomes the target (not an input number)
    cutoff_pos = -1
    if make_24_pos >= 0:
        cutoff_pos = make_24_pos
    if answer_24_pos >= 0 and (cutoff_pos < 0 or answer_24_pos < cutoff_pos):
        cutoff_pos = answer_24_pos
    
    if cutoff_pos >= 0:
        # Only keep numbers that appear before the cutoff
        # We'll extract numbers from the substring before cutoff
        before_cutoff = question[:cutoff_pos]
        nums = _nums_from_str(before_cutoff)
    
    # Remove trailing 24s (in case they still appear)
    while nums and nums[-1] == 24:
        nums = nums[:-1]
    
    # Take the last 4 numbers (should be the input numbers)
    if len(nums) >= 4:
        return nums[-4:]
    elif len(nums) > 0:
        # If we have fewer than 4, return what we have (shouldn't happen with proper questions)
        return nums
    else:
        # Fallback: try to extract from the original question, removing 24s
        all_nums = _nums_from_str(question)
        filtered = [n for n in all_nums if n != 24]
        return filtered[-4:] if len(filtered) >= 4 else filtered

def _uses_exact_multiset(expr: str, target_nums: List[int]) -> bool:
    return Counter(_nums_from_str(expr)) == Counter(target_nums)

_EXPR_LINE_RE = re.compile(r'(?i)(?:^|\n)\s*(?:expr\s*:\s*)?([0-9\(\)\s\+\-\*/]+)(?:\s*=\s*24)?(?:\s*answer\s*:\s*24)?\s*(?:$|\n)')
# Fallback: grab any arithmetic-looking chunk
_EXPR_FALLBACK_RE = re.compile(r'[0-9\(\)\s\+\-\*/]{3,}')

def _extract_all_game24_exprs(text: str) -> List[str]:
    cand = []
    for m in _EXPR_LINE_RE.finditer(text or ""):
        s = (m.group(1) or "").strip()
        if s:
            cand.append(s)
    # If nothing matched labeled form, fall back to any arithmetic chunk
    if not cand:
        for m in _EXPR_FALLBACK_RE.finditer(text or ""):
            s = m.group(0).strip()
            if s:
                cand.append(s)
    # De-dup, keep order
    seen, out = set(), []
    for s in cand:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out[:8]  # keep it small

def _detect_task_mode(question: str) -> str:
    q = (question or "").lower()
    if "to make 24" in q or "make 24" in q:
        return "game24"
    if "single word: yes or no" in q:
        return "boolean"
    return "numeric"

# --------------------------
# Prompt helpers
# --------------------------

def _seed_tail(task_mode: str, target_nums: List[int]) -> str:
    if task_mode == "boolean":
        return "Answer strictly with a single word: yes or no."
    if task_mode == "game24":
        # Provide examples based on the numbers
        example = ""
        if len(target_nums) == 4:
            # Try to give a helpful example
            if 6 in target_nums and 4 in target_nums:
                example = "Example: For [1, 1, 4, 6], try: EXPR: (6 * 4) * (1 / 1)  ANSWER: 24 (which equals 24 * 1 = 24)"
            elif 8 in target_nums and 3 in target_nums:
                example = "Example: For [1, 1, 3, 8], try: EXPR: (8 * 3) * (1 / 1)  ANSWER: 24 (which equals 24 * 1 = 24)"
            elif all(n == 6 for n in target_nums):
                example = "Example: For [6, 6, 6, 6], try: EXPR: (6 + 6) * (6 / 6) + 6 + 6  ANSWER: 24 (which equals 12 * 1 + 12 = 24)"
        
        return (
            f"Task: Use ONLY the numbers {target_nums} exactly once each with + - * / and parentheses.\n"
            "The expression MUST evaluate to exactly 24. Calculate it step by step to verify.\n"
            "Do NOT use the number 24 in your expression. Do NOT invent numbers. Do NOT concatenate digits.\n"
            f"{example}\n"
            "Return ONE line only in this exact format:\n"
            "EXPR: <expression>  ANSWER: 24"
        )
    return "Give a brief plan and a tentative numeric result. End with: ANSWER: <number>"

def _refine_prompt(task_mode: str, question: str, attempt_text: str, feedback: str, target_nums: List[int]) -> str:
    if task_mode == "boolean":
        return (
            "Refine and verify the final decision.\n"
            "Return only 'yes' or 'no'.\n"
            f"Question: {question}\n"
            f"Current attempt: {attempt_text}\n"
            f"Feedback: {feedback}\n"
            "Answer:"
        )
    if task_mode == "game24":
        return (
            "CRITICAL: You must create an expression that evaluates to EXACTLY 24.\n"
            f"Use ONLY the numbers {target_nums} exactly once each with + - * / and parentheses.\n"
            "Do NOT use the number 24 in your expression. Do NOT invent numbers. Do NOT concatenate digits.\n"
            f"Question: {question}\n"
            f"Current attempt: {attempt_text}\n"
            f"Feedback: {feedback}\n"
            "Before submitting, calculate your expression step by step to verify it equals exactly 24.\n"
            "Return ONE line only in this exact format:\n"
            "EXPR: <expression>  ANSWER: 24\n"
            "Expression:"
        )
    return (
        "Refine and verify the final numeric result.\n"
        f"Question: {question}\n"
        f"Current attempt: {attempt_text}\n"
        f"Feedback: {feedback}\n"
        "If a correction is needed, fix it. End with: ANSWER: <number>\n"
        "Answer:"
    )

def _score_text_for_mode(text: str, task_mode: str, target_nums: Optional[List[int]] = None) -> float:
    if not text:
        return 0.0
    if task_mode == "boolean":
        return 1.0 if ("yes" in text.lower() or "no" in text.lower()) else 0.2
    if task_mode == "game24":
        exprs = _extract_all_game24_exprs(text)
        best = 0.0
        for e in exprs:
            val = _safe_eval(e)
            # Heavily penalize if not exactly 24
            if val is not None and math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9):
                # Perfect score if equals 24 AND uses correct numbers
                nums_ok = 1.0 if (target_nums and _uses_exact_multiset(e, target_nums)) else 0.0
                if nums_ok:
                    return 1.0  # Perfect match
                else:
                    best = max(best, 0.8)  # Right value, wrong numbers
            else:
                # Penalize based on distance from 24
                if val is None:
                    close = 0.0
                else:
                    # Strong penalty for being far from 24
                    distance = abs(val - 24.0)
                    if distance > 10:
                        close = 0.0  # Too far, reject
                    else:
                        close = max(0.0, 1.0 - (distance / 10.0))  # Linear penalty
                nums_ok = 1.0 if (target_nums and _uses_exact_multiset(e, target_nums)) else 0.0
                # Weight exact 24 much more heavily
                best = max(best, 0.9 * close + 0.1 * nums_ok)
        return best if best > 0 else 0.1
    # numeric
    return 1.0 if extract_numeric_answer(text) else 0.2

# --------------------------
# BAMoT main
# --------------------------

def run_item(
    item: Dict[str, Any],
    gateway: ModelGateway,
    cot_system: str,
    *,
    seeds: int = 4,
    budget_tokens: int = 1200,
    no_triage: bool = False,
    no_consensus: bool = False,
    seed_tokens: int = 80,
    refine_tokens: int = 320,
    early_stop_gold: bool = False,     # ignored for game24
    gold_value: Optional[str] = None,  # ignored for game24
    refine_topk: int = 3,
    seed_budget_frac: float = 0.30,
    task_mode: Optional[str] = None,  # Allow explicit task_mode override
    **kwargs
) -> Dict[str, Any]:

    question = item.get("question", "")
    # Use passed task_mode if provided, otherwise auto-detect
    if task_mode is None:
        task_mode = _detect_task_mode(question)
    
    # For Game24, prefer numbers from item dict if available (more reliable)
    if task_mode == "game24":
        target_nums = item.get("numbers")
        if not target_nums:
            # Fallback to extraction from question
            target_nums = _numbers_from_question(question)
    else:
        target_nums = []
    
    gold_answer = item.get("answer")  # For early stopping on non-game24 tasks

    total_prompt = 0
    total_comp = 0
    latencies: List[float] = []

    # ---------- 1) MICRO-SEEDS ----------
    seed_pool: List[Tuple[str, Optional[str], float]] = []
    seed_budget_limit = int(max(1, budget_tokens * seed_budget_frac))

    def _try_take_valid(text: str) -> Optional[str]:
        """Return first valid answer for early stopping."""
        if task_mode == "game24":
            for e in _extract_all_game24_exprs(text):
                if target_nums and _uses_exact_multiset(e, target_nums):
                    val = _safe_eval(e)
                    if val is not None and math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9):
                        return e
            return None
        elif task_mode == "boolean":
            # Check if we have a clear yes/no answer
            txt_lower = text.lower()
            has_yes = "yes" in txt_lower and "no" not in txt_lower
            has_no = "no" in txt_lower and "yes" not in txt_lower
            if has_yes:
                return "yes"
            elif has_no:
                return "no"
            return None
        else:  # numeric
            # For numeric tasks, check if we have a valid answer
            pred = extract_numeric_answer(text)
            if pred and gold_answer:
                # Early stop if we match gold (optional, controlled by early_stop_gold)
                if early_stop_gold:
                    try:
                        pred_f = float(pred)
                        gold_f = float(str(gold_answer))
                        if math.isclose(pred_f, gold_f, rel_tol=1e-9, abs_tol=1e-9):
                            return pred
                    except:
                        pass
            return pred if pred else None

    for i in range(seeds):
        if (total_prompt + total_comp) >= seed_budget_limit and len(seed_pool) > 0:
            break

        tmp = ModelGateway(
            model=gateway.model,
            temperature=min(1.0, 0.2 + 0.2 * i),
            max_tokens=seed_tokens,
            backend=gateway.backend,
            llama_model_path=getattr(gateway, '_llama_model_path', None),
            llama_ctx=getattr(gateway, '_llama_ctx', 4096),
            llama_threads=getattr(gateway, '_llama_threads', None)
        )
        prompt = f"{question}\n\n{_seed_tail(task_mode, target_nums)}"
        out = tmp.chat(system_prompt=cot_system, user_prompt=prompt)

        txt = out["text"]

        # Early-stop if any valid answer already appears
        got_answer = _try_take_valid(txt)
        if got_answer:
            u = out.get("usage", {}) or {}
            total_prompt += u.get("prompt_tokens", 0) or 0
            total_comp += u.get("completion_tokens", 0) or 0
            if out.get("latency") is not None:
                latencies.append(out["latency"])
            return {
                "text": f"[PASS seed]\n{txt}",
                "pred": got_answer,
                "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
                "latency": sum(latencies)/len(latencies) if latencies else out.get("latency"),
            }

        if task_mode == "boolean":
            pred = "yes" if ("yes" in txt.lower() and "no" not in txt.lower()) else ("no" if "no" in txt.lower() else None)
        elif task_mode == "game24":
            # store the *closest* expr (if any) as 'pred' to guide triage
            exprs = _extract_all_game24_exprs(txt)
            pred = None
            best = -1.0
            for e in exprs:
                val = _safe_eval(e)
                close = 0.0 if val is None else 1.0 / (1.0 + abs(val - 24.0))
                nums_ok = 1.0 if (target_nums and _uses_exact_multiset(e, target_nums)) else 0.0
                s = 0.7 * close + 0.3 * nums_ok
                if s > best:
                    best, pred = s, e
        else:
            pred = extract_numeric_answer(txt)

        sc = 1.0 if no_triage else _score_text_for_mode(txt, task_mode, target_nums=target_nums)
        seed_pool.append((txt, pred, sc))

        u = out.get("usage", {}) or {}
        total_prompt += u.get("prompt_tokens", 0) or 0
        total_comp   += u.get("completion_tokens", 0) or 0
        if out.get("latency") is not None:
            latencies.append(out["latency"])

    if not seed_pool:
        tmp = ModelGateway(
            model=gateway.model,
            temperature=0.2,
            max_tokens=seed_tokens,
            backend=gateway.backend,
            llama_model_path=getattr(gateway, '_llama_model_path', None),
            llama_ctx=getattr(gateway, '_llama_ctx', 4096),
            llama_threads=getattr(gateway, '_llama_threads', None)
        )
        prompt = f"{question}\n\n{_seed_tail(task_mode, target_nums)}"
        out = tmp.chat(system_prompt=cot_system, user_prompt=prompt)
        txt = out["text"]
        pred = extract_numeric_answer(txt) if task_mode != "game24" else None
        seed_pool.append((txt, pred, _score_text_for_mode(txt, task_mode, target_nums=target_nums)))
        u = out.get("usage", {}) or {}
        total_prompt += u.get("prompt_tokens", 0) or 0
        total_comp   += u.get("completion_tokens", 0) or 0

    best_pool = sorted(seed_pool, key=lambda x: x[2], reverse=True)
    token_spend = total_prompt + total_comp

    # ---------- 2) SELECTIVE REFINEMENTS ----------
    refine_gws = [
        ModelGateway(
            model=gateway.model,
            temperature=t,
            max_tokens=refine_tokens,
            backend=gateway.backend,
            llama_model_path=getattr(gateway, '_llama_model_path', None),
            llama_ctx=getattr(gateway, '_llama_ctx', 4096),
            llama_threads=getattr(gateway, '_llama_threads', None)
        )
        for t in (0.2, 0.4, 0.6, 0.8)
    ]
    rr = 0

    def _feedback_for(text: str) -> str:
        if task_mode != "game24":
            return "Fix mistakes and finalize."
        # generate feedback from the *best* candidate inside this text
        exprs = _extract_all_game24_exprs(text)
        if not exprs:
            return "No valid arithmetic expression detected. Produce a single arithmetic expression that uses only the given numbers."
        # choose the closest one for feedback
        best_e, best_close = exprs[0], -1.0
        for e in exprs:
            val = _safe_eval(e)
            close = 0.0 if val is None else 1.0 / (1.0 + abs((val or 0) - 24.0))
            if close > best_close:
                best_close, best_e = close, e
        nums_ok = _uses_exact_multiset(best_e, target_nums)
        val = _safe_eval(best_e)
        bits = []
        if not nums_ok:
            used_nums = sorted(_nums_from_str(best_e))
            bits.append(f"ERROR: You must use EACH of {sorted(target_nums)} exactly once. You used {used_nums}.")
        if val is None:
            bits.append("ERROR: Your expression could not be evaluated. Use only + - * / and parentheses, no other operations.")
        elif not math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9):
            # More specific feedback about the value
            diff = abs(val - 24.0)
            if diff < 1:
                bits.append(f"CLOSE but not exact: Your expression evaluates to {val}, which is {diff} away from 24. Adjust to get exactly 24.")
            elif val < 24:
                bits.append(f"TOO LOW: Your expression evaluates to {val}, which is {24 - val} less than 24. You need to increase the value.")
            else:
                bits.append(f"TOO HIGH: Your expression evaluates to {val}, which is {val - 24} more than 24. You need to decrease the value.")
            bits.append("Try different operations or grouping. Remember: the result must be EXACTLY 24.")
        if not bits:
            bits.append("Expression looks correct! Verify it equals exactly 24.")
        return " ".join(bits)

    # Refinement loop: check budget BEFORE each API call
    while token_spend < budget_tokens:
        # Check if we can afford another refinement (estimate)
        estimated_refine_cost = refine_tokens * 2  # rough estimate: prompt + completion
        if token_spend + estimated_refine_cost > budget_tokens:
            break
        
        best_pool.sort(key=lambda x: x[2], reverse=True)
        idx = rr % min(max(1, refine_topk), len(best_pool))
        base_txt, _, _ = best_pool[idx]

        fb = _feedback_for(base_txt)
        refine_prompt = _refine_prompt(task_mode, question, base_txt, fb, target_nums)

        gw_i = refine_gws[rr % len(refine_gws)]
        out = gw_i.chat(system_prompt=cot_system, user_prompt=refine_prompt)
        rr += 1

        new_txt = out["text"]

        # Early-stop if any valid answer appears now
        got_answer = _try_take_valid(new_txt)
        if got_answer:
            u = out.get("usage", {}) or {}
            total_prompt += u.get("prompt_tokens", 0) or 0
            total_comp   += u.get("completion_tokens", 0) or 0
            lat = out.get("latency")
            if lat is not None: latencies.append(lat)
            return {
                "text": f"[PASS refine]\n{new_txt}",
                "pred": got_answer,
                "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
                "latency": sum(latencies)/len(latencies) if latencies else None,
            }

        # Otherwise keep best attempt for next round
        if task_mode == "boolean":
            new_pred = "yes" if ("yes" in new_txt.lower() and "no" not in new_txt.lower()) else ("no" if "no" in new_txt.lower() else None)
        elif task_mode == "game24":
            new_pred = None
            best = -1.0
            for e in _extract_all_game24_exprs(new_txt):
                val = _safe_eval(e)
                close = 0.0 if val is None else 1.0 / (1.0 + abs((val or 0) - 24.0))
                nums_ok = 1.0 if _uses_exact_multiset(e, target_nums) else 0.0
                s = 0.7 * close + 0.3 * nums_ok
                if s > best:
                    best, new_pred = s, e
        else:
            new_pred = extract_numeric_answer(new_txt)

        new_sc = 1.0 if no_triage else _score_text_for_mode(new_txt, task_mode, target_nums=target_nums)
        best_pool.append((new_txt, new_pred, new_sc))

        u = out.get("usage", {}) or {}
        pt = u.get("prompt_tokens", 0) or 0
        ct = u.get("completion_tokens", 0) or 0
        total_prompt += pt
        total_comp += ct
        token_spend = total_prompt + total_comp
        if out.get("latency") is not None:
            latencies.append(out["latency"])

        # dedup by surface (pred if present, else text)
        dedup = {}
        for t_, p_, s_ in best_pool:
            key = (p_ or t_)[:256]
            if key not in dedup or s_ > dedup[key][2]:
                dedup[key] = (t_, p_, s_)
        best_pool = list(dedup.values())

        # Check budget after updating (safety check)
        if token_spend >= budget_tokens:
            break

    # ---------- 3) CONSENSUS / best ----------
    best_pool.sort(key=lambda x: x[2], reverse=True)
    
    if no_consensus:
        # Just take the top-scored candidate
        final_pred = best_pool[0][1] if best_pool else None
    else:
        # Implement consensus: majority voting for top-K candidates
        top_k_for_consensus = min(3, len(best_pool))
        top_candidates = best_pool[:top_k_for_consensus]
        
        # Collect predictions (non-None)
        preds = [c[1] for c in top_candidates if c[1] is not None]
        
        if not preds:
            # Fallback to top candidate even if pred is None
            final_pred = best_pool[0][1] if best_pool else None
        elif len(preds) == 1:
            final_pred = preds[0]
        else:
            # Majority vote (or weighted by score)
            if task_mode == "boolean":
                # Simple majority for yes/no
                yes_count = sum(1 for p in preds if str(p).lower().strip() in ("yes", "true", "y", "1"))
                no_count = sum(1 for p in preds if str(p).lower().strip() in ("no", "false", "n", "0"))
                final_pred = "yes" if yes_count > no_count else ("no" if no_count > 0 else preds[0])
            elif task_mode == "game24":
                # For game24, prioritize expressions that exactly equal 24
                valid_exprs = []
                close_exprs = []  # Expressions close to 24
                for c in top_candidates:
                    if c[1]:  # has a prediction
                        for e in _extract_all_game24_exprs(c[0]):  # extract from text
                            if target_nums and _uses_exact_multiset(e, target_nums):
                                val = _safe_eval(e)
                                if val is not None:
                                    if math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9):
                                        valid_exprs.append(e)  # Perfect match
                                    elif abs(val - 24.0) < 2.0:  # Within 2 of 24
                                        close_exprs.append((e, abs(val - 24.0)))
                if valid_exprs:
                    final_pred = valid_exprs[0]  # take first perfect match
                elif close_exprs:
                    # Sort by distance to 24, take closest
                    close_exprs.sort(key=lambda x: x[1])
                    final_pred = close_exprs[0][0]
                else:
                    final_pred = preds[0]  # fallback to top prediction
            else:  # numeric
                # For numeric, try to find consensus by checking if multiple agree
                # (within tolerance)
                numeric_preds = []
                for p in preds:
                    try:
                        numeric_preds.append(float(str(p)))
                    except:
                        pass
                if numeric_preds:
                    # Use median or most common value
                    numeric_preds.sort()
                    median_idx = len(numeric_preds) // 2
                    final_pred = str(int(numeric_preds[median_idx]) if numeric_preds[median_idx].is_integer() else numeric_preds[median_idx])
                else:
                    final_pred = preds[0]

    trace = "\n\n==== TOP CANDIDATES ====\n\n" + "\n\n----\n\n".join([c[0] for c in best_pool[:3]])
    avg_latency = (sum(latencies) / len(latencies)) if latencies else None
    return {
        "text": trace,
        "pred": final_pred,
        "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
        "latency": avg_latency,
    }
