# run.py (resume-safe, append-safe)
import argparse, os, time, csv, importlib
from datetime import datetime
import pandas as pd
from tqdm import tqdm

from utils.model_gateway import ModelGateway
# from utils.logger import CSVLogger  # (Replaced by direct csv append for resume safety)
from utils.evals import is_correct, bool_match

PROMPTS = {
    "cot_system": open("prompts/cot_prompt.txt","r").read().strip(),
}

def load_dataset(name: str):
    if name == "gsm8k":
        mod = importlib.import_module("loaders.gsm8k")
        return mod.load()
    if name == "game24":
        mod = importlib.import_module("loaders.game24")
        return mod.load()
    if name == "strategyqa":
        mod = importlib.import_module("loaders.strategyqa")
        return mod.load()
    
    if name == "math500":
        mod = importlib.import_module("loaders.math500")
        return mod.load()
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

def _load_done_ids(csv_path: str) -> set:
    """
    Read an existing results CSV and return the set of item IDs already completed.
    Safe to call on non-existent files; returns empty set.
    """
    done = set()
    if csv_path and os.path.isfile(csv_path):
        try:
            with open(csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "id" in row and row["id"]:
                        done.add(row["id"])
        except Exception:
            # If the file is partially written/corrupt, skip resume to be safe.
            pass
    return done

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=["cot","sc_cot","bamot","tot","got","fot"])
    ap.add_argument("--dataset", required=True, choices=["gsm8k","game24","strategyqa","math500"])
    ap.add_argument("--limit", type=int, default=None, help="Run only the first N items (after resume filtering).")

    # model settings
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--max_tokens", type=int, default=512)

    # shared experiment params
    ap.add_argument("--budget_tokens", type=int, default=800)  # used by BAMoT
    ap.add_argument("--seeds", type=int, default=4)            # used by BAMoT
    ap.add_argument("--sc_samples", type=int, default=5)       # used by SC-CoT
    ap.add_argument("--exp_name", default=None)

    # ===== BAMoT ablations / controls =====
    ap.add_argument("--bamot_no_triage", action="store_true")
    ap.add_argument("--bamot_no_consensus", action="store_true")
    ap.add_argument("--bamot_seed_tokens", type=int, default=80)     # micro-seed token cap
    ap.add_argument("--bamot_refine_tokens", type=int, default=256)  # refinement token cap
    ap.add_argument("--bamot_early_stop_gold", action="store_true")  # stop if pred == gold
    ap.add_argument("--bamot_gold_value", default=None)              # override gold (e.g., "24")
    ap.add_argument("--bamot_refine_topk", type=int, default=2)

    # ===== ToT / GoT / FoT knobs for fair, budget-matched runs =====
    ap.add_argument("--tot_branch", type=int, default=3)
    ap.add_argument("--tot_depth", type=int, default=2)

    ap.add_argument("--got_beam", type=int, default=4)
    ap.add_argument("--got_steps", type=int, default=3)

    ap.add_argument("--fot_trees", type=int, default=3)
    ap.add_argument("--fot_branch", type=int, default=2)
    ap.add_argument("--fot_depth", type=int, default=1)

    # ===== NEW: persistence & resume =====
    ap.add_argument("--out_dir", type=str, default="results", help="Directory to write per-run CSVs.")
    ap.add_argument("--resume_from", type=str, default="", help="Existing CSV path to resume from (skip already-done IDs).")
    
    args = ap.parse_args()

    # --- output paths ---
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    exp_name = args.exp_name or f"{args.method}_{args.dataset}_{int(time.time())}"
    out_csv = os.path.join(args.out_dir, f"{exp_name}.csv")

    # --- dataset ---
    data = load_dataset(args.dataset)

    # --- resume filtering ---
    # If --resume_from is provided, use it; otherwise, resume into our own out_csv if it already exists.
    resume_csv = args.resume_from if args.resume_from else (out_csv if os.path.exists(out_csv) else "")
    done_ids = _load_done_ids(resume_csv)
    if len(done_ids) > 0:
        print(f"[resume] Found {len(done_ids)} completed IDs in: {resume_csv}")

    pending = [ex for ex in data if ex.get("id") not in done_ids]
    if args.limit is not None:
        pending = pending[:args.limit]
    print(f"[plan] Total loaded: {len(data)} | To run now: {len(pending)} | Skipped(done): {len(done_ids)}")

    # --- model gateway ---
    gw = ModelGateway(model=args.model, temperature=args.temperature, max_tokens=args.max_tokens)
    cot_system = PROMPTS["cot_system"]
    run_fn = get_method(args.method)

    # --- open CSV in append mode; write header if new/empty ---
    fieldnames = ["id","method","dataset","gold","pred","correct","prompt_toks","completion_toks","latency_sec"]
    write_header = (not os.path.isfile(out_csv)) or (os.path.getsize(out_csv) == 0)
    f = open(out_csv, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    if write_header:
        writer.writeheader()
        f.flush()
        os.fsync(f.fileno())

    # --- main loop ---
    for item in tqdm(data, desc=f"Running {args.method} on {args.dataset}"):
        t0 = time.time()  # fallback latency timer

        # Always start with a copy; customize prompt per dataset without leaking i2
        item_for_method = dict(item)

        if args.dataset == "strategyqa":
            q = item.get("question", "")
            item_for_method["question"] = (
                "Answer strictly with a single word: yes or no.\n"
                "Question: " + q + "\n"
                "Answer:"
            )

        elif args.dataset in ("aime", "math500"):
            q = item.get("question", "")
            item_for_method["question"] = (
                "Give the final answer as a single number only (no words, no units). "
                "End with: ANSWER: <number>\n"
                "Question: " + q + "\n"
                "Answer:"
            )


        # --- dispatch per method ---
        if args.method == "sc_cot":
            out = run_fn(item_for_method, gateway=gw, cot_system=cot_system, sc_samples=args.sc_samples)

        elif args.method == "bamot":
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
                refine_topk=args.bamot_refine_topk,   # NEW

            )

        elif args.method == "tot":
            out = run_fn(
                item_for_method,
                gateway=gw,
                cot_system=cot_system,
                branch=args.tot_branch,
                depth=args.tot_depth,
            )

        elif args.method == "got":
            out = run_fn(
                item_for_method,
                gateway=gw,
                cot_system=cot_system,
                steps=args.got_steps,
                beam=args.got_beam,
            )

        elif args.method == "fot":
            out = run_fn(
                item_for_method,
                gateway=gw,
                cot_system=cot_system,
                trees=args.fot_trees,
                branch=args.fot_branch,
                depth=args.fot_depth,
            )

        else:  # "cot"
            out = run_fn(item_for_method, gateway=gw, cot_system=cot_system)

        pred = out.get("pred")
        gold = item.get("answer")

        # StrategyQA uses boolean evaluator; others numeric/text
        if args.dataset == "strategyqa":
            corr = bool_match(pred, gold)
        else:
            corr = is_correct(pred, gold)

        usage = out.get("usage", {}) or {}
        latency = out.get("latency", None)
        if latency is None:
            latency = time.time() - t0

        # --- append row + flush for durability ---
        writer.writerow({
            "id": item.get("id"),
            "method": args.method,
            "dataset": args.dataset,
            "gold": gold,
            "pred": pred,
            "correct": int(bool(corr)),
            "prompt_toks": usage.get("prompt_tokens", None),
            "completion_toks": usage.get("completion_tokens", None),
            "latency_sec": latency
        })
        f.flush()
        os.fsync(f.fileno())

    f.close()

    # --- summary (for this exp only) ---
    df = pd.read_csv(out_csv)
    acc = df["correct"].mean()
    print(f"\n== Summary: {args.method} on {args.dataset} ==")
    print(df.head())
    print(f"Accuracy: {acc*100:.1f}%  ({df['correct'].sum()}/{len(df)})")
    print(f"\nSaved: {out_csv}")

if __name__ == "__main__":
    main()
