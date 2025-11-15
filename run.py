# run.py — resume-safe, limit-aware, shuffle-capable runner
import argparse, os, time, csv, importlib, random
from datetime import datetime
import pandas as pd
from tqdm import tqdm

from utils.model_gateway import ModelGateway
from utils.evals import is_correct, bool_match

# ---------- Prompts ----------
# ---------- System prompts (dataset-specific) ----------
def _sys_math_numeric():
    return ("You are a careful math tutor. Solve the problem step by step, clearly. "
            "When you finish, put your final numeric answer after the tag: ANSWER: <number>")

def _sys_boolean_yesno():
    return ("You are a precise verifier. Answer strictly with a single word: yes or no. "
            "Do not include any numbers, punctuation, or extra text.")

def _sys_game24():
    # *** NEW: a Game24-specific system with NO numeric 'ANSWER:<number>' rule ***
    return ("You are a symbolic arithmetic solver. Your job is to output exactly ONE expression "
            "that evaluates to 24 using the four given numbers exactly once each and only the "
            "operators +, -, *, / and parentheses. Do not provide explanations. "
            "Return a single expression on one line and end your message with: ANSWER: 24")

SYSTEMS = {
    "math_numeric": _sys_math_numeric(),
    "boolean": _sys_boolean_yesno(),
    "game24": _sys_game24(),  # <-- was numeric before; now proper Game24
}
# ---------- Dataset / Method loaders ----------
def load_dataset(name: str):
    if name == "gsm8k":
        return importlib.import_module("loaders.gsm8k").load()
    if name == "game24":
        return importlib.import_module("loaders.game24").load()
    if name == "strategyqa":
        return importlib.import_module("loaders.strategyqa").load()
    if name == "math500":
        return importlib.import_module("loaders.math500").load()
    raise ValueError(f"Unknown dataset: {name}")

def get_method(name: str):
    if name == "cot":
        return importlib.import_module("methods.cot").run_item
    if name == "sc_cot":
        return importlib.import_module("methods.sc_cot").run_item
    if name == "bamot":
        return importlib.import_module("methods.bamot").run_item
    if name == "tot":
        return importlib.import_module("methods.tot").run_item
    if name == "got":
        return importlib.import_module("methods.got").run_item
    if name == "fot":
        return importlib.import_module("methods.fot").run_item
    raise ValueError(f"Unknown method: {name}")

# ---------- Helpers ----------
def _load_done_ids(csv_path: str) -> set:
    """
    Read an existing results CSV and return the set of item IDs already completed.
    Safe to call on non-existent or partially written files; returns empty set on failure.
    """
    done = set()
    if csv_path and os.path.isfile(csv_path):
        try:
            with open(csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rid = (row.get("id") or "").strip()
                    if rid:
                        done.add(rid)
        except Exception:
            pass
    return done

def _get_example_id(ex, idx=None):
    for k in ("id", "qid", "question_id", "uid", "index"):
        if k in ex:
            return str(ex[k])
    return str(idx)  # fallback: positional index

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=["cot","sc_cot","bamot","tot","got","fot"])
    ap.add_argument("--dataset", required=True, choices=["gsm8k","game24","strategyqa","math500"])
    ap.add_argument("--limit", type=int, default=None, help="Run only the first N items (after resume filtering).")
    ap.add_argument("--shuffle", action="store_true", help="Shuffle pending items before applying --limit.")
    ap.add_argument("--random_seed", type=int, default=42, help="RNG seed for --shuffle.")

    # model settings
    ap.add_argument("--model", default="gpt-4o-mini",
                    help="Model identifier (OpenAI name, llama label, etc.)")
    ap.add_argument("--backend", choices=["openai", "llama_cpp"], default="openai",
                    help="LLM backend to use. 'openai' (default) or 'llama_cpp' for local LLaMA models.")
    ap.add_argument("--llama_model_path", type=str, default=os.getenv("LLAMA_MODEL_PATH", ""),
                    help="Path to GGUF/GGML model for llama_cpp backend (or set LLAMA_MODEL_PATH).")
    ap.add_argument("--llama_ctx", type=int, default=4096, help="Context window for llama_cpp backend.")
    ap.add_argument("--llama_threads", type=int, default=None, help="CPU threads for llama_cpp backend.")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--max_tokens", type=int, default=512)

    # shared experiment params
    ap.add_argument("--budget_tokens", type=int, default=800)  # used by BAMoT
    ap.add_argument("--seeds", type=int, default=4)            # used by BAMoT
    ap.add_argument("--sc_samples", type=int, default=5)       # used by SC-CoT
    ap.add_argument("--exp_name", default=None)

    # ===== BAMoT controls / ablations =====
    ap.add_argument("--bamot_no_triage", action="store_true")
    ap.add_argument("--bamot_no_consensus", action="store_true")
    ap.add_argument("--bamot_seed_tokens", type=int, default=80)     # micro-seed token cap
    ap.add_argument("--bamot_refine_tokens", type=int, default=256)  # refinement token cap
    ap.add_argument("--bamot_early_stop_gold", action="store_true")  # stop if pred == gold
    ap.add_argument("--bamot_gold_value", default=None)              # override gold (e.g., "24")
    ap.add_argument("--bamot_refine_topk", type=int, default=2)

    # ===== ToT / GoT / FoT knobs (keep light for small budgets) =====
    ap.add_argument("--tot_branch", type=int, default=3)
    ap.add_argument("--tot_depth", type=int, default=2)
    ap.add_argument("--got_beam", type=int, default=4)
    ap.add_argument("--got_steps", type=int, default=3)
    ap.add_argument("--fot_trees", type=int, default=3)
    ap.add_argument("--fot_branch", type=int, default=2)
    ap.add_argument("--fot_depth", type=int, default=1)

    # ===== Persistence & resume =====
    ap.add_argument("--out_dir", type=str, default="results", help="Directory to write per-run CSVs.")
    ap.add_argument("--resume_from", type=str, default="", help="Existing CSV path to resume from (skip already-done IDs).")

    args = ap.parse_args()

    # --- output paths ---
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    exp_name = args.exp_name or f"{args.method}_{args.dataset}_{int(time.time())}"
    out_csv = os.path.join(args.out_dir, f"{exp_name}.csv")

    # --- dataset ---
    examples = load_dataset(args.dataset)

    # --- resume plan ---
    resume_csv = args.resume_from if args.resume_from else (out_csv if os.path.exists(out_csv) else "")
    done_ids = _load_done_ids(resume_csv)
    if len(done_ids) > 0:
        print(f"[resume] Found {len(done_ids)} completed IDs in: {resume_csv}")

    # Build (id, example) pairs and remove done
    indexed = [( _get_example_id(ex, i), ex ) for i, ex in enumerate(examples)]
    pending_pairs = [(eid, ex) for (eid, ex) in indexed if eid not in done_ids]

    # Shuffle BEFORE limiting if requested
    if args.shuffle and len(pending_pairs) > 1:
        rng = random.Random(args.random_seed)
        rng.shuffle(pending_pairs)

    # Apply limit AFTER resume filtering (and shuffling, if any)
    if args.limit is not None:
        pending_pairs = pending_pairs[:int(args.limit)]

    print(f"[plan] Total loaded: {len(examples)} | To run now: {len(pending_pairs)} | Skipped(done): {len(done_ids)}")

    # --- model gateway & method ---
    # --- model gateway & method ---
    gw = ModelGateway(
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        backend=args.backend,
        llama_model_path=args.llama_model_path,
        llama_ctx=args.llama_ctx,
        llama_threads=args.llama_threads,
    )

    # dataset-specific system prompt
    if args.dataset == "strategyqa":
        cot_system = SYSTEMS["boolean"]
    elif args.dataset in ("gsm8k", "math500"):
        cot_system = SYSTEMS["math_numeric"]
    elif args.dataset == "game24":
        cot_system = SYSTEMS["game24"]
    else:
        cot_system = SYSTEMS["math_numeric"]

    run_fn = get_method(args.method)

    # --- CSV setup (append-safe) ---
    fieldnames = ["id","method","dataset","gold","pred","correct","prompt_toks","completion_toks","latency_sec"]
    write_header = (not os.path.isfile(out_csv)) or (os.path.getsize(out_csv) == 0)
    f = open(out_csv, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    if write_header:
        writer.writeheader()
        f.flush(); os.fsync(f.fileno())

    # --- main loop over ONLY the pending/limited items ---
    pbar_desc = f"Running {args.method} on {args.dataset}"
    for ex_id, ex in tqdm(pending_pairs, total=len(pending_pairs), desc=pbar_desc):
        t0 = time.time()  # fallback latency

        # Copy example; shape prompt per dataset without mutating original
        item_for_method = dict(ex)

        if args.dataset == "strategyqa":
            q = ex.get("question", "")
            item_for_method["question"] = (
                "Answer strictly with a single word: yes or no.\n"
                "Question: " + q + "\n"
                "Answer:"
            )
        elif args.dataset in ("math500","gsm8k"):  # numeric only formatting
            q = ex.get("question", "")
            item_for_method["question"] = (
                "Give the final answer as a single number only (no words, no units). "
                "End with: ANSWER: <number>\n"
                "Question: " + q + "\n"
                "Answer:"
            )
        elif args.dataset == "game24":
            q = ex.get("question","")
            item_for_method["question"] = (
                q + "\n\nOnly output ONE expression using all four numbers exactly once. "
                    "No steps. End with: ANSWER: 24"
            )    
        # (game24/gsm8k often fine as-is; keep loaders' formatting)

        # --- dispatch ---
        try:
            if args.method == "sc_cot":
                out = run_fn(item_for_method, gateway=gw, cot_system=cot_system, sc_samples=args.sc_samples)

            elif args.method == "bamot":
              task_mode = "boolean" if args.dataset == "strategyqa" else ("game24" if args.dataset == "game24" else "numeric")
              out = run_fn(
                  item_for_method,
                  gateway=gw,
                  cot_system=cot_system,
                  seeds=args.seeds,
                  budget_tokens=args.budget_tokens,
                  no_triage=args.bamot_no_triage,
                  no_consensus=args.bamot_no_consensus,
                  seed_tokens=args.bamot_seed_tokens,
                  refine_tokens=args.bamot_refine_tokens,
                  early_stop_gold=args.bamot_early_stop_gold,
                  gold_value=args.bamot_gold_value,
                  refine_topk=args.bamot_refine_topk,
                  task_mode=task_mode,   # <-- IMPORTANT
              )


            elif args.method == "tot":
                out = run_fn(item_for_method, gateway=gw, cot_system=cot_system, branch=args.tot_branch, depth=args.tot_depth)

            elif args.method == "got":
                out = run_fn(item_for_method, gateway=gw, cot_system=cot_system, steps=args.got_steps, beam=args.got_beam)

            elif args.method == "fot":
                out = run_fn(item_for_method, gateway=gw, cot_system=cot_system, trees=args.fot_trees, branch=args.fot_branch, depth=args.fot_depth)

            else:  # "cot"
                out = run_fn(item_for_method, gateway=gw, cot_system=cot_system)

        except Exception as e:
            # Log a failed row but keep the run going
            out = {"pred": f"ERROR: {type(e).__name__}: {e}", "usage": {}, "latency": time.time() - t0}

        pred = out.get("pred")
        gold = ex.get("answer")

        # StrategyQA uses boolean evaluator; others numeric/text
        if args.dataset == "strategyqa":
            corr = bool_match(pred, gold)
        elif args.dataset == "game24":
            # For game24 we grade by checking the returned expression against the question
            from utils.evals import is_game24_correct
            corr = is_game24_correct(out.get("text", "") if pred is None else str(pred), ex.get("question", ""))
        else:
            corr = is_correct(pred, gold)


        usage = out.get("usage", {}) or {}
        latency = out.get("latency", None)
        if latency is None:
            latency = time.time() - t0

        writer.writerow({
            "id": ex_id,
            "method": args.method,
            "dataset": args.dataset,
            "gold": gold,
            "pred": pred,
            "correct": int(bool(corr)),
            "prompt_toks": usage.get("prompt_tokens", None),
            "completion_toks": usage.get("completion_tokens", None),
            "latency_sec": latency
        })
        f.flush(); os.fsync(f.fileno())

    f.close()

    # --- summary (for this exp only) ---
    try:
        df = pd.read_csv(out_csv)
        acc = df["correct"].mean()
        print(f"\n== Summary: {args.method} on {args.dataset} ==")
        print(df.head())
        print(f"Accuracy: {acc*100:.1f}%  ({df['correct'].sum()}/{len(df)})")
    except Exception as e:
        print(f"Saved: {out_csv} (could not summarize: {e})")
        return

    print(f"\nSaved: {out_csv}")

if __name__ == "__main__":
    main()
