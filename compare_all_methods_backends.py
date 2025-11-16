#!/usr/bin/env python3
"""
Comprehensive comparison of all methods across all backends.
Compares: BAMoT, CoT, SC-CoT, ToT, GoT, FoT
Across: GPT-4o-mini, LLaMA, Qwen
"""

import pandas as pd
import os
import glob
from pathlib import Path

def load_results(pattern: str) -> pd.DataFrame:
    """Load all CSV files matching pattern."""
    files = glob.glob(f"results/{pattern}")
    if not files:
        return None
    dfs = []
    for f in sorted(files):
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"Warning: Could not load {f}: {e}")
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)

def summarize_method(df: pd.DataFrame, method_name: str, backend: str) -> dict:
    """Compute summary statistics for a method."""
    if df is None or len(df) == 0:
        return {
            "method": method_name,
            "backend": backend,
            "accuracy": 0.0,
            "total_items": 0,
            "avg_tokens": 0.0,
            "avg_latency": 0.0,
            "total_tokens": 0,
        }
    
    # Filter out error rows
    df_clean = df[~df["pred"].astype(str).str.startswith("ERROR:", na=False)] if "pred" in df.columns else df
    if len(df_clean) == 0:
        df_clean = df
    
    correct = df_clean["correct"].sum() if "correct" in df_clean.columns else 0
    total = len(df_clean)
    accuracy = (correct / total * 100) if total > 0 else 0.0
    
    # Token usage - check for different column name patterns
    if "prompt_toks" in df_clean.columns and "completion_toks" in df_clean.columns:
        # Calculate total tokens per row
        df_clean = df_clean.copy()
        df_clean["total_tokens"] = df_clean["prompt_toks"].fillna(0) + df_clean["completion_toks"].fillna(0)
        avg_tokens = df_clean["total_tokens"].mean()
        total_tokens = df_clean["total_tokens"].sum()
    elif "tokens_used" in df_clean.columns:
        avg_tokens = df_clean["tokens_used"].mean()
        total_tokens = df_clean["tokens_used"].sum()
    elif "total_tokens" in df_clean.columns:
        avg_tokens = df_clean["total_tokens"].mean()
        total_tokens = df_clean["total_tokens"].sum()
    else:
        avg_tokens = 0.0
        total_tokens = 0
    
    # Latency
    if "latency_sec" in df_clean.columns:
        avg_latency = df_clean["latency_sec"].mean()
    elif "latency" in df_clean.columns:
        avg_latency = df_clean["latency"].mean()
    else:
        avg_latency = 0.0
    
    return {
        "method": method_name,
        "backend": backend,
        "accuracy": accuracy,
        "total_items": total,
        "avg_tokens": avg_tokens,
        "avg_latency": avg_latency,
        "total_tokens": total_tokens,
    }

def main():
    print("=" * 80)
    print("COMPREHENSIVE METHOD & BACKEND COMPARISON")
    print("=" * 80)
    print()
    
    methods = ["bamot", "cot", "sc_cot", "tot", "got", "fot"]
    backends = {
        "gpt4o-mini": "gpt4o-mini",
        "llama": "llama",
        "qwen": "qwen",
    }
    dataset = "game24"
    
    results = []
    
    # Load results for each method-backend combination
    for method in methods:
        for backend_key, backend_label in backends.items():
            if backend_key == "gpt4o-mini":
                pattern = f"{method}_g24_100.csv"
            elif backend_key == "llama":
                pattern = f"{method}_g24_llama_100.csv"
            elif backend_key == "qwen":
                # Try fixed results first, then fall back to original
                pattern_fixed = f"{method}_g24_qwen_100_fixed.csv"
                pattern_orig = f"{method}_g24_qwen_100.csv"
                files_fixed = glob.glob(f"results/{pattern_fixed}")
                if files_fixed:
                    pattern = pattern_fixed
                else:
                    pattern = pattern_orig
            else:
                continue
            
            df = load_results(pattern)
            summary = summarize_method(df, method.upper(), backend_label)
            results.append(summary)
    
    # Create comparison DataFrame
    comparison_df = pd.DataFrame(results)
    
    if len(comparison_df) == 0:
        print("No results found. Make sure experiments have been run.")
        return
    
    # Display summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print()
    
    # Pivot for better readability
    pivot_acc = comparison_df.pivot(index="method", columns="backend", values="accuracy")
    pivot_tokens = comparison_df.pivot(index="method", columns="backend", values="avg_tokens")
    pivot_latency = comparison_df.pivot(index="method", columns="backend", values="avg_latency")
    
    print("\nACCURACY (%):")
    print("-" * 80)
    print(pivot_acc.round(2).to_string())
    print()
    
    print("\nAVERAGE TOKENS PER ITEM:")
    print("-" * 80)
    print(pivot_tokens.round(0).to_string())
    print()
    
    print("\nAVERAGE LATENCY (seconds):")
    print("-" * 80)
    print(pivot_latency.round(3).to_string())
    print()
    
    # Detailed comparison
    print("\n" + "=" * 80)
    print("DETAILED COMPARISON")
    print("=" * 80)
    print()
    print(comparison_df.to_string(index=False))
    print()
    
    # Save to CSV
    output_file = "results/comprehensive_comparison.csv"
    comparison_df.to_csv(output_file, index=False)
    print(f"\nSaved detailed comparison to: {output_file}")
    
    # BAMoT vs Others analysis
    print("\n" + "=" * 80)
    print("BAMoT vs OTHER METHODS (Average across backends)")
    print("=" * 80)
    print()
    
    bamot_results = comparison_df[comparison_df["method"] == "BAMOT"]
    other_results = comparison_df[comparison_df["method"] != "BAMOT"]
    
    if len(bamot_results) > 0:
        bamot_avg_acc = bamot_results["accuracy"].mean()
        bamot_avg_tokens = bamot_results["avg_tokens"].mean()
        bamot_avg_latency = bamot_results["avg_latency"].mean()
        
        print(f"BAMoT Average Accuracy: {bamot_avg_acc:.2f}%")
        print(f"BAMoT Average Tokens: {bamot_avg_tokens:.0f}")
        print(f"BAMoT Average Latency: {bamot_avg_latency:.3f}s")
        print()
        
        for method in other_results["method"].unique():
            method_results = other_results[other_results["method"] == method]
            method_avg_acc = method_results["accuracy"].mean()
            method_avg_tokens = method_results["avg_tokens"].mean()
            method_avg_latency = method_results["avg_latency"].mean()
            
            acc_diff = bamot_avg_acc - method_avg_acc
            token_diff = bamot_avg_tokens - method_avg_tokens
            latency_diff = bamot_avg_latency - method_avg_latency
            
            print(f"{method}:")
            print(f"  Accuracy: {method_avg_acc:.2f}% (BAMoT {'+' if acc_diff > 0 else ''}{acc_diff:.2f}%)")
            print(f"  Tokens: {method_avg_tokens:.0f} (BAMoT {'+' if token_diff > 0 else ''}{token_diff:.0f})")
            print(f"  Latency: {method_avg_latency:.3f}s (BAMoT {'+' if latency_diff > 0 else ''}{latency_diff:.3f}s)")
            print()

if __name__ == "__main__":
    main()

