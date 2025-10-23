import argparse, os, time
import importlib
import pandas as pd
from tqdm import tqdm

from utils.model_gateway import ModelGateway
from utils.logger import CSVLogger
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
    if name == "aime":
        mod = importlib.import_module("loaders.aime")
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=["cot","sc_cot","bamot","tot","got","fot"])
    ap.add_argument("--dataset", required=True, choices=["gsm8k","game24","strategyqa","aime","math500"])

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

    # ===== ToT / GoT / FoT knobs for fair, budget-matched runs =====
    ap.add_argument("--tot_branch", type=int, default=3)
    ap.add_argument("--tot_depth", type=int, default=2)

    ap.add_argument("--got_beam", type=int, default=4)
    ap.add_argument("--got_steps", type=int, default=3)

    ap.add_argument("--fot_trees", type=int, default=3)
    ap.add_argument("--fot_branch", type=int, default=2)
    ap.add_argument("--fot_depth", type=int, default=1)

    args = ap.parse_args()

    exp_name = args.exp_name or f"{args.method}_{args.dataset}_{int(time.time())}"
    os.makedirs("results", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # logger
    csv_path = f"results/{exp_name}.csv"
    log = CSVLogger(csv_path, header=["id","method","dataset","gold","pred","correct","prompt_toks","completion_toks","latency_sec"])

    data = load_dataset(args.dataset)
    run_fn = get_method(args.method)

    # Gateway configured with *default* max_tokens (methods may override)
    gw = ModelGateway(model=args.model, temperature=args.temperature, max_tokens=args.max_tokens)
    cot_system = PROMPTS["cot_system"]

    for item in tqdm(data, desc=f"Running {args.method} on {args.dataset}"):
        if args.method == "sc_cot":
            out = run_fn(item, gateway=gw, cot_system=cot_system, sc_samples=args.sc_samples)

        elif args.method == "bamot":
            out = run_fn(
                item,
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
            )

        elif args.method == "tot":
            out = run_fn(
                item,
                gateway=gw,
                cot_system=cot_system,
                branch=args.tot_branch,
                depth=args.tot_depth,
            )

        elif args.method == "got":
            out = run_fn(
                item,
                gateway=gw,
                cot_system=cot_system,
                steps=args.got_steps,
                beam=args.got_beam,
            )

        elif args.method == "fot":
            out = run_fn(
                item,
                gateway=gw,
                cot_system=cot_system,
                trees=args.fot_trees,
                branch=args.fot_branch,
                depth=args.fot_depth,
            )

        else:  # "cot"
            out = run_fn(item, gateway=gw, cot_system=cot_system)

        pred = out.get("pred")
        gold = item.get("answer")
        corr = is_correct(pred, gold)
        # Use boolean evaluator for StrategyQA; otherwise keep your numeric/text is_correct
        if args.dataset == "strategyqa":
            corr = bool_match(pred, gold)
        else:
            corr = is_correct(pred, gold)
        usage = out.get("usage", {}) or {}
        lat = out.get("latency", None)

        log.log([
            item.get("id"),
            args.method,
            args.dataset,
            gold,
            pred,
            int(bool(corr)),
            usage.get("prompt_tokens", None),
            usage.get("completion_tokens", None),
            lat
        ])

    # print summary
    df = pd.read_csv(csv_path)
    acc = df["correct"].mean()
    print(f"\n== Summary: {args.method} on {args.dataset} ==")
    print(df.head())
    print(f"Accuracy: {acc*100:.1f}%  ({df['correct'].sum()}/{len(df)})")
    df.to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path}")

if __name__ == "__main__":
    main()
