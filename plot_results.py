import os, glob, sys
import pandas as pd

def main(argv):
    # Directory where CSVs live (default: ./results)
    in_dir = "results"
    if len(argv) >= 1:
        in_dir = argv[0]

    # Methods & datasets you actually used (no AIME)
    methods  = ["bamot","cot","sc_cot","tot","got","fot"]
    datasets = ["game24","strategyqa","math500","gsm8k"]  # include gsm8k if you’ll run it later

    frames = []
    for m in methods:
        for d in datasets:
            pattern = os.path.join(in_dir, f"*{m}_{d}_*.csv")
            for csv in glob.glob(pattern):
                try:
                    df = pd.read_csv(csv)
                    frames.append(df)
                except Exception:
                    pass

    if not frames:
        print("No CSVs found to plot/summarize. Check your results directory.")
        return

    all_df = pd.concat(frames, ignore_index=True)

    # Example aggregate table
    summary = (all_df
               .groupby(["method","dataset"], dropna=False)
               .agg(acc=("correct","mean"),
                    mean_prompt=("prompt_toks","mean"),
                    mean_comp=("completion_toks","mean"),
                    mean_latency=("latency_sec","mean"),
               ).reset_index())
    summary["acc"] = (summary["acc"]*100).round(1)

    os.makedirs("figures", exist_ok=True)
    summary.to_csv(os.path.join("figures","summary.csv"), index=False)
    print("\n== Aggregate summary (saved to figures/summary.csv) ==")
    print(summary.to_string(index=False))

if __name__ == "__main__":
    main(sys.argv[1:])
