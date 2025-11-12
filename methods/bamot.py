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
    nums = _nums_from_str(question)
    if nums and nums[-1] == 24:
        nums = nums[:-1]
    # keep the last four before the trailing 24, which matches our loaders' phrasing
    return nums[-4:]

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
        return (
            f"Task: Use the numbers {target_nums} exactly once each with + - * / and parentheses to make 24.\n"
            "Do NOT invent new numbers (e.g., '1' if not provided). Do NOT concatenate digits.\n"
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
            "Refine and verify ONE valid expression that equals 24 using the numbers "
            f"{target_nums} exactly once each with + - * / and parentheses.\n"
            "Do NOT invent numbers and do NOT concatenate digits.\n"
            f"Question: {question}\n"
            f"Current attempt: {attempt_text}\n"
            f"Feedback: {feedback}\n"
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
            close = 0.0 if val is None else 1.0 / (1.0 + abs(val - 24.0))
            nums_ok = 1.0 if (target_nums and _uses_exact_multiset(e, target_nums)) else 0.0
            best = max(best, 0.7 * close + 0.3 * nums_ok)
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
    **kwargs
) -> Dict[str, Any]:

    question = item.get("question", "")
    task_mode = _detect_task_mode(question)
    target_nums = _numbers_from_question(question) if task_mode == "game24" else []

    total_prompt = 0
    total_comp = 0
    latencies: List[float] = []

    # ---------- 1) MICRO-SEEDS ----------
    seed_pool: List[Tuple[str, Optional[str], float]] = []
    seed_budget_limit = int(max(1, budget_tokens * seed_budget_frac))

    def _try_take_valid(text: str) -> Optional[str]:
        """Return first valid expr == 24 using exact nums; else None."""
        if task_mode != "game24":
            return None
        for e in _extract_all_game24_exprs(text):
            if target_nums and _uses_exact_multiset(e, target_nums):
                val = _safe_eval(e)
                if val is not None and math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9):
                    return e
        return None

    for i in range(seeds):
        if (total_prompt + total_comp) >= seed_budget_limit and len(seed_pool) > 0:
            break

        tmp = ModelGateway(model=gateway.model,
                           temperature=min(1.0, 0.2 + 0.2 * i),
                           max_tokens=seed_tokens)
        prompt = f"{question}\n\n{_seed_tail(task_mode, target_nums)}"
        out = tmp.chat(system_prompt=cot_system, user_prompt=prompt)

        txt = out["text"]

        # Early-stop if any valid expr already appears
        got_expr = _try_take_valid(txt)
        if got_expr:
            u = out.get("usage", {}) or {}
            return {
                "text": f"[PASS seed]\n{txt}",
                "pred": got_expr,
                "usage": {"prompt_tokens": u.get("prompt_tokens", 0), "completion_tokens": u.get("completion_tokens", 0)},
                "latency": out.get("latency"),
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
        tmp = ModelGateway(model=gateway.model, temperature=0.2, max_tokens=seed_tokens)
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
        ModelGateway(model=gateway.model, temperature=t, max_tokens=refine_tokens)
        for t in (0.2, 0.4, 0.6, 0.8)
    ]
    rr = 0

    def _feedback_for(text: str) -> str:
        if task_mode != "game24":
            return "Fix mistakes and finalize."
        # generate feedback from the *best* candidate inside this text
        exprs = _extract_all_game24_exprs(text)
        if not exprs:
            return "No valid arithmetic expression detected. Produce a single arithmetic expression."
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
            bits.append(f"Use EACH of {sorted(target_nums)} exactly once; you used {sorted(_nums_from_str(best_e))}.")
        if val is None:
            bits.append("Your expression could not be evaluated. Use only + - * / and parentheses.")
        elif not math.isclose(val, 24.0, rel_tol=1e-9, abs_tol=1e-9):
            bits.append(f"Your expression evaluates to {val}, not 24.")
        if not bits:
            bits.append("Looks valid — keep the same numbers exactly once and ensure it equals 24.")
        return " ".join(bits)

    while token_spend <= budget_tokens:
        best_pool.sort(key=lambda x: x[2], reverse=True)
        idx = rr % min(max(1, refine_topk), len(best_pool))
        base_txt, _, _ = best_pool[idx]

        fb = _feedback_for(base_txt)
        refine_prompt = _refine_prompt(task_mode, question, base_txt, fb, target_nums)

        gw_i = refine_gws[rr % len(refine_gws)]
        out = gw_i.chat(system_prompt=cot_system, user_prompt=refine_prompt)
        rr += 1

        new_txt = out["text"]

        # Early-stop if any valid expr appears now
        got_expr = _try_take_valid(new_txt)
        if got_expr:
            u = out.get("usage", {}) or {}
            total_prompt += u.get("prompt_tokens", 0) or 0
            total_comp   += u.get("completion_tokens", 0) or 0
            lat = out.get("latency")
            if lat is not None: latencies.append(lat)
            return {
                "text": f"[PASS refine]\n{new_txt}",
                "pred": got_expr,
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

        if (pt + ct) > 0 and token_spend + (pt + ct) > budget_tokens:
            break

    # ---------- 3) CONSENSUS / best ----------
    best_pool.sort(key=lambda x: x[2], reverse=True)
    final_pred = best_pool[0][1]  # for game24 we want the best expr we found (may still be None)

    trace = "\n\n==== TOP CANDIDATES ====\n\n" + "\n\n----\n\n".join([c[0] for c in best_pool[:3]])
    avg_latency = (sum(latencies) / len(latencies)) if latencies else None
    return {
        "text": trace,
        "pred": final_pred,
        "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp},
        "latency": avg_latency,
    }
