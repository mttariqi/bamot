import sys, pandas as pd, numpy as np
import matplotlib.pyplot as plt

def p50(x): return np.percentile(x.dropna().values, 50) if len(x.dropna()) else np.nan
def p90(x): return np.percentile(x.dropna().values, 90) if len(x.dropna()) else np.nan

def main(paths):
    frames = []
    for p in paths:
        df = pd.read_csv(p)
        df["source"] = p.split("/")[-1].replace(".csv","")
        frames.append(df)
    all_df = pd.concat(frames, ignore_index=True)

    # coerce numerics
    for col in ["prompt_toks","completion_toks","latency_sec","correct"]:
        if col in all_df.columns:
            all_df[col] = pd.to_numeric(all_df[col], errors="coerce")

    summary = (all_df
               .groupby(["method","dataset"], as_index=False)
               .agg(acc=("correct","mean"),
                    p50lat=("latency_sec", p50),
                    p90lat=("latency_sec", p90),
                    prompt=("prompt_toks","sum"),
                    completion=("completion_toks","sum"))
               .sort_values(["dataset","method"]))

    print(summary)

    labels = summary["method"] + " (" + summary["dataset"] + ")"
    x = np.arange(len(labels))

    # Accuracy
    fig1, ax1 = plt.subplots(figsize=(9,4))
    ax1.bar(x, summary["acc"]*100)
    ax1.set_xticks(x, labels, rotation=30, ha="right")
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_ylim(0, 110)
    fig1.tight_layout()
    fig1.savefig("results/_acc.png", dpi=160)

    # Latency P50/P90
    fig2, ax2 = plt.subplots(figsize=(9,4))
    width = 0.35
    ax2.bar(x - width/2, summary["p50lat"], width, label="P50")
    ax2.bar(x + width/2, summary["p90lat"], width, label="P90")
    ax2.set_xticks(x, labels, rotation=30, ha="right")
    ax2.set_ylabel("Latency (s)")
    ax2.legend()
    fig2.tight_layout()
    fig2.savefig("results/_latency.png", dpi=160)

    # Total tokens
    total_tokens = (summary["prompt"].fillna(0) + summary["completion"].fillna(0))
    fig3, ax3 = plt.subplots(figsize=(9,4))
    ax3.bar(x, total_tokens)
    ax3.set_xticks(x, labels, rotation=30, ha="right")
    ax3.set_ylabel("Total tokens")
    fig3.tight_layout()
    fig3.savefig("results/_tokens.png", dpi=160)

if __name__ == "__main__":
    main(sys.argv[1:])
