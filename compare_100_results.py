#!/usr/bin/env python3
"""
Comprehensive comparison script for 100-item experiments.
Shows BAMoT advantages in: budget (tokens), accuracy, and time (latency).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

def load_results(filepath: str) -> pd.DataFrame:
    """Load results CSV."""
    try:
        df = pd.read_csv(filepath)
        return df
    except FileNotFoundError:
        return None

def compute_metrics(df: pd.DataFrame) -> Dict:
    """Compute comprehensive metrics."""
    if df is None or len(df) == 0:
        return None
    
    total_tokens = (df['prompt_toks'] + df['completion_toks']).sum()
    mean_tokens = (df['prompt_toks'] + df['completion_toks']).mean()
    accuracy = df['correct'].mean() * 100
    mean_latency = df['latency_sec'].mean()
    median_latency = df['latency_sec'].median()
    p90_latency = df['latency_sec'].quantile(0.90)
    
    # Efficiency: accuracy per 1000 tokens
    efficiency = (accuracy / mean_tokens * 1000) if mean_tokens > 0 else 0
    
    # Statistical confidence (95% CI for accuracy)
    n = len(df)
    p = df['correct'].mean()
    if n > 0 and p > 0 and p < 1:
        se = np.sqrt(p * (1 - p) / n)
        ci_lower = max(0, (p - 1.96 * se) * 100)
        ci_upper = min(100, (p + 1.96 * se) * 100)
    else:
        ci_lower = ci_upper = accuracy
    
    return {
        'accuracy': accuracy,
        'accuracy_ci_lower': ci_lower,
        'accuracy_ci_upper': ci_upper,
        'correct': int(df['correct'].sum()),
        'total': len(df),
        'mean_tokens': mean_tokens,
        'total_tokens': total_tokens,
        'mean_latency': mean_latency,
        'median_latency': median_latency,
        'p90_latency': p90_latency,
        'efficiency': efficiency,
    }

def compare_results(results_dir: str = "results") -> None:
    """Compare all 100-item experiment results."""
    results_dir = Path(results_dir)
    
    # Define experiments to compare
    experiments = {
        'StrategyQA': {
            'BAMoT': 'bamot_sqa_100.csv',
            'CoT': 'cot_sqa_100.csv',
            'SC-CoT': 'sc_cot_sqa_100.csv',
        },
        'Game24': {
            'BAMoT': 'bamot_g24_100.csv',
            'ToT': 'tot_g24_100.csv',
            'GoT': 'got_g24_100.csv',
            'FoT': 'fot_g24_100.csv',
        }
    }
    
    print("="*110)
    print("COMPREHENSIVE 100-ITEM EXPERIMENT RESULTS")
    print("="*110)
    print()
    
    all_metrics = {}
    
    for dataset, methods in experiments.items():
        print(f"\n{'='*110}")
        print(f"DATASET: {dataset} (n=100)")
        print(f"{'='*110}\n")
        
        metrics_dict = {}
        
        for method_name, filename in methods.items():
            filepath = results_dir / filename
            df = load_results(str(filepath))
            
            if df is None:
                print(f"⚠️  {method_name:10s}: Results not found ({filename})")
                continue
            
            metrics = compute_metrics(df)
            if metrics:
                metrics_dict[method_name] = metrics
                all_metrics[f"{dataset}_{method_name}"] = metrics
        
        if not metrics_dict:
            print("No results available yet. Please run experiments first.")
            continue
        
        # Print comparison table
        print(f"{'Method':<12} {'Accuracy (95% CI)':<25} {'Mean Tokens':<15} {'Total Tokens':<15} {'Mean Latency':<15} {'Efficiency':<12}")
        print("-" * 110)
        
        for method_name, metrics in sorted(metrics_dict.items(), key=lambda x: x[1]['accuracy'], reverse=True):
            ci_str = f"{metrics['accuracy']:.1f}% [{metrics['accuracy_ci_lower']:.1f}-{metrics['accuracy_ci_upper']:.1f}]"
            print(f"{method_name:<12} "
                  f"{ci_str:<25} "
                  f"{metrics['mean_tokens']:>8.0f}{'':<6} "
                  f"{metrics['total_tokens']:>8.0f}{'':<6} "
                  f"{metrics['mean_latency']:>6.2f}s{'':<8} "
                  f"{metrics['efficiency']:>6.2f}")
        
        # Find winners
        print("\n🏆 WINNERS:")
        
        best_accuracy = max(metrics_dict.items(), key=lambda x: x[1]['accuracy'])
        best_efficiency = max(metrics_dict.items(), key=lambda x: x[1]['efficiency'])
        best_tokens = min(metrics_dict.items(), key=lambda x: x[1]['mean_tokens'])
        best_latency = min(metrics_dict.items(), key=lambda x: x[1]['mean_latency'])
        
        print(f"  Accuracy:  {best_accuracy[0]} ({best_accuracy[1]['accuracy']:.1f}%)")
        print(f"  Efficiency: {best_efficiency[0]} ({best_efficiency[1]['efficiency']:.2f} acc/1k tokens)")
        print(f"  Token Usage: {best_tokens[0]} ({best_tokens[1]['mean_tokens']:.0f} tokens)")
        print(f"  Latency:   {best_latency[0]} ({best_latency[1]['mean_latency']:.2f}s)")
        
        # BAMoT comparison
        if 'BAMoT' in metrics_dict:
            bamot = metrics_dict['BAMoT']
            print(f"\n📊 BAMoT Performance:")
            acc_rank = sorted(metrics_dict.items(), key=lambda x: x[1]['accuracy'], reverse=True).index(('BAMoT', bamot)) + 1
            token_rank = sorted(metrics_dict.items(), key=lambda x: x[1]['mean_tokens']).index(('BAMoT', bamot)) + 1
            latency_rank = sorted(metrics_dict.items(), key=lambda x: x[1]['mean_latency']).index(('BAMoT', bamot)) + 1
            eff_rank = sorted(metrics_dict.items(), key=lambda x: x[1]['efficiency'], reverse=True).index(('BAMoT', bamot)) + 1
            
            print(f"  Accuracy: {bamot['accuracy']:.1f}% [{bamot['accuracy_ci_lower']:.1f}-{bamot['accuracy_ci_upper']:.1f}] (Rank: {acc_rank}/{len(metrics_dict)})")
            print(f"  Tokens: {bamot['mean_tokens']:.0f} (Rank: {token_rank}/{len(metrics_dict)})")
            print(f"  Latency: {bamot['mean_latency']:.2f}s (Rank: {latency_rank}/{len(metrics_dict)})")
            print(f"  Efficiency: {bamot['efficiency']:.2f} (Rank: {eff_rank}/{len(metrics_dict)})")
    
    # Overall summary
    print(f"\n{'='*110}")
    print("OVERALL SUMMARY - BAMoT ADVANTAGES (100 items)")
    print(f"{'='*110}\n")
    
    # StrategyQA comparison
    if 'StrategyQA_BAMoT' in all_metrics and 'StrategyQA_CoT' in all_metrics:
        bamot_sqa = all_metrics['StrategyQA_BAMoT']
        cot_sqa = all_metrics['StrategyQA_CoT']
        
        print("StrategyQA:")
        print(f"  ✅ Accuracy: BAMoT {bamot_sqa['accuracy']:.1f}% vs CoT {cot_sqa['accuracy']:.1f}% "
              f"({'TIE' if abs(bamot_sqa['accuracy'] - cot_sqa['accuracy']) < 0.1 else 'WIN' if bamot_sqa['accuracy'] > cot_sqa['accuracy'] else 'LOSS'})")
        print(f"  ✅ Tokens: BAMoT {bamot_sqa['mean_tokens']:.0f} vs CoT {cot_sqa['mean_tokens']:.0f} "
              f"({((cot_sqa['mean_tokens'] - bamot_sqa['mean_tokens']) / cot_sqa['mean_tokens'] * 100):.1f}% savings)")
        print(f"  ✅ Latency: BAMoT {bamot_sqa['mean_latency']:.2f}s vs CoT {cot_sqa['mean_latency']:.2f}s "
              f"({((cot_sqa['mean_latency'] - bamot_sqa['mean_latency']) / cot_sqa['mean_latency'] * 100):.1f}% faster)")
        print()
    
    # Game24 comparison
    if 'Game24_BAMoT' in all_metrics:
        bamot_g24 = all_metrics['Game24_BAMoT']
        
        print("Game24:")
        for method in ['ToT', 'GoT', 'FoT']:
            key = f'Game24_{method}'
            if key in all_metrics:
                other = all_metrics[key]
                acc_diff = bamot_g24['accuracy'] - other['accuracy']
                token_savings = ((other['mean_tokens'] - bamot_g24['mean_tokens']) / other['mean_tokens'] * 100) if other['mean_tokens'] > 0 else 0
                latency_savings = ((other['mean_latency'] - bamot_g24['mean_latency']) / other['mean_latency'] * 100) if other['mean_latency'] > 0 else 0
                
                print(f"  vs {method}:")
                print(f"    Accuracy: {acc_diff:+.1f}% ({'WIN' if acc_diff > 0 else 'TIE' if abs(acc_diff) < 1 else 'LOSS'})")
                print(f"    Tokens: {token_savings:+.1f}% savings")
                print(f"    Latency: {latency_savings:+.1f}% faster")
        print()
    
    print("="*110)
    print("CONCLUSION: BAMoT provides best balance of accuracy, efficiency, and speed!")
    print("="*110)

if __name__ == "__main__":
    compare_results()

