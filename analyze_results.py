#!/usr/bin/env python3
"""
Analyze and compare results from all experiments.
Generates comparison tables and visualizations.
"""
import pandas as pd
import glob
import os
from pathlib import Path

def load_all_results():
    """Load all result CSVs."""
    results_dir = Path("results")
    all_data = []
    
    for csv_file in results_dir.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
            # Extract method and dataset from filename
            parts = csv_file.stem.split("_")
            if len(parts) >= 2:
                method = parts[0]
                dataset = parts[1]
                # Extract budget if present
                budget = None
                for p in parts:
                    if p.startswith("B") and p[1:].isdigit():
                        budget = int(p[1:])
                        break
                
                df["method"] = method
                df["dataset"] = dataset
                df["budget"] = budget
                df["exp_file"] = csv_file.name
                all_data.append(df)
        except Exception as e:
            print(f"Warning: Could not load {csv_file}: {e}")
    
    if not all_data:
        print("No results found!")
        return None
    
    return pd.concat(all_data, ignore_index=True)

def generate_summary(df):
    """Generate summary statistics."""
    summary = df.groupby(["method", "dataset", "budget"]).agg({
        "correct": ["mean", "sum", "count"],
        "prompt_toks": "mean",
        "completion_toks": "mean",
        "latency_sec": "mean"
    }).round(2)
    
    summary.columns = ["accuracy", "correct_count", "total_count", "mean_prompt_toks", "mean_comp_toks", "mean_latency"]
    summary["mean_total_tokens"] = summary["mean_prompt_toks"] + summary["mean_comp_toks"]
    summary["accuracy_pct"] = (summary["accuracy"] * 100).round(1)
    
    return summary

def print_comparison_table(df):
    """Print formatted comparison table."""
    summary = generate_summary(df)
    
    print("\n" + "="*100)
    print("COMPREHENSIVE RESULTS COMPARISON")
    print("="*100)
    
    for dataset in df["dataset"].unique():
        print(f"\n{'='*100}")
        print(f"DATASET: {dataset.upper()}")
        print(f"{'='*100}")
        print(f"{'Method':<10} {'Budget':<8} {'Accuracy':<10} {'Tokens':<10} {'Latency':<10} {'Items':<8}")
        print("-"*100)
        
        dataset_data = summary.loc[summary.index.get_level_values("dataset") == dataset]
        
        for budget in sorted(df[df["dataset"] == dataset]["budget"].unique()):
            budget_data = dataset_data.loc[dataset_data.index.get_level_values("budget") == budget]
            
            for method in ["bamot", "cot", "sc_cot", "tot", "got", "fot"]:
                try:
                    row = budget_data.loc[(method, dataset, budget)]
                    acc = f"{row['accuracy_pct']:.1f}%"
                    tokens = f"{row['mean_total_tokens']:.0f}"
                    latency = f"{row['mean_latency']:.2f}s"
                    items = f"{int(row['total_count'])}"
                    print(f"{method.upper():<10} {budget:<8} {acc:<10} {tokens:<10} {latency:<10} {items:<8}")
                except KeyError:
                    pass
        
        print()
    
    # Overall summary
    print(f"\n{'='*100}")
    print("OVERALL SUMMARY BY METHOD")
    print(f"{'='*100}")
    overall = df.groupby("method").agg({
        "correct": "mean",
        "prompt_toks": "mean",
        "completion_toks": "mean",
        "latency_sec": "mean"
    })
    overall["total_tokens"] = overall["prompt_toks"] + overall["completion_toks"]
    overall["accuracy_pct"] = (overall["correct"] * 100).round(1)
    
    print(f"{'Method':<10} {'Accuracy':<10} {'Mean Tokens':<15} {'Mean Latency':<15}")
    print("-"*100)
    for method in ["bamot", "cot", "sc_cot", "tot", "got", "fot"]:
        try:
            row = overall.loc[method]
            print(f"{method.upper():<10} {row['accuracy_pct']:.1f}%{'':<5} {row['total_tokens']:.0f}{'':<8} {row['latency_sec']:.2f}s")
        except KeyError:
            pass

def save_summary_csv(df):
    """Save summary to CSV."""
    summary = generate_summary(df)
    output_file = "results/comprehensive_summary.csv"
    summary.to_csv(output_file)
    print(f"\n✅ Summary saved to: {output_file}")

def main():
    """Main analysis function."""
    print("Loading results...")
    df = load_all_results()
    
    if df is None or len(df) == 0:
        print("No results to analyze. Run experiments first.")
        return
    
    print(f"Loaded {len(df)} result rows from {df['exp_file'].nunique()} experiments")
    
    print_comparison_table(df)
    save_summary_csv(df)
    
    print("\n" + "="*100)
    print("Analysis complete!")
    print("="*100)

if __name__ == "__main__":
    main()

