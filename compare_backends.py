#!/usr/bin/env python3
"""
Compare results between GPT-4o-mini (OpenAI) and LLaMA backends.
"""

import csv
from pathlib import Path
from typing import Dict, Optional

def load_results(filepath: str) -> Optional[Dict]:
    """Load and analyze results from CSV."""
    if not Path(filepath).exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        return None
    
    total = len(rows)
    correct = sum(1 for r in rows if r['correct'].strip() in ('1', 'True', 'true', 'TRUE'))
    prompt_toks = [int(r['prompt_toks']) for r in rows]
    comp_toks = [int(r['completion_toks']) for r in rows]
    latency = [float(r['latency_sec']) for r in rows]
    
    acc = correct / total * 100 if total else 0
    mean_tokens = sum(p + c for p, c in zip(prompt_toks, comp_toks)) / total if total else 0
    mean_latency = sum(latency) / total if total else 0
    total_tokens = sum(p + c for p, c in zip(prompt_toks, comp_toks))
    
    return {
        'accuracy': acc,
        'correct': correct,
        'total': total,
        'mean_tokens': mean_tokens,
        'total_tokens': total_tokens,
        'mean_latency': mean_latency,
        'min_latency': min(latency) if latency else 0,
        'max_latency': max(latency) if latency else 0,
    }

def compare_backends():
    """Compare GPT-4o-mini vs LLaMA results."""
    results_dir = Path("results")
    
    experiments = {
        'StrategyQA': {
            'GPT-4o-mini': 'bamot_sqa_gpt4o_20.csv',
            'LLaMA 3.2 1B': 'bamot_sqa_llama_20.csv',
        },
        'Game24': {
            'GPT-4o-mini': 'bamot_g24_gpt4o_20.csv',
            'LLaMA 3.2 1B': 'bamot_g24_llama_20.csv',
        }
    }
    
    print("="*80)
    print("BACKEND COMPARISON: GPT-4o-mini vs LLaMA 3.2 1B")
    print("="*80)
    print()
    
    for dataset, backends in experiments.items():
        print(f"{'='*80}")
        print(f"DATASET: {dataset} (n=20)")
        print(f"{'='*80}\n")
        
        gpt_results = None
        llama_results = None
        
        for backend_name, filename in backends.items():
            filepath = results_dir / filename
            results = load_results(str(filepath))
            
            if results:
                if 'GPT' in backend_name:
                    gpt_results = results
                else:
                    llama_results = results
        
        if not gpt_results or not llama_results:
            print("⚠️  Missing results - waiting for experiments to complete...")
            print()
            continue
        
        # Print comparison table
        print(f"{'Metric':<20} {'GPT-4o-mini':<20} {'LLaMA 3.2 1B':<20} {'Difference':<20}")
        print("-"*80)
        
        # Accuracy
        acc_diff = llama_results['accuracy'] - gpt_results['accuracy']
        gpt_acc_str = f"{gpt_results['accuracy']:.1f}% ({gpt_results['correct']}/{gpt_results['total']})"
        llama_acc_str = f"{llama_results['accuracy']:.1f}% ({llama_results['correct']}/{llama_results['total']})"
        print(f"{'Accuracy':<20} "
              f"{gpt_acc_str:<20} "
              f"{llama_acc_str:<20} "
              f"{acc_diff:+.1f}%")
        
        # Tokens
        token_diff = llama_results['mean_tokens'] - gpt_results['mean_tokens']
        token_pct = (token_diff / gpt_results['mean_tokens'] * 100) if gpt_results['mean_tokens'] > 0 else 0
        print(f"{'Mean Tokens':<20} "
              f"{gpt_results['mean_tokens']:>8.0f}{'':<11} "
              f"{llama_results['mean_tokens']:>8.0f}{'':<11} "
              f"{token_diff:+.0f} ({token_pct:+.1f}%)")
        
        # Latency
        lat_diff = llama_results['mean_latency'] - gpt_results['mean_latency']
        lat_pct = (lat_diff / gpt_results['mean_latency'] * 100) if gpt_results['mean_latency'] > 0 else 0
        print(f"{'Mean Latency':<20} "
              f"{gpt_results['mean_latency']:>6.2f}s{'':<13} "
              f"{llama_results['mean_latency']:>6.2f}s{'':<13} "
              f"{lat_diff:+.2f}s ({lat_pct:+.1f}%)")
        
        # Total tokens
        total_diff = llama_results['total_tokens'] - gpt_results['total_tokens']
        print(f"{'Total Tokens':<20} "
              f"{gpt_results['total_tokens']:>8.0f}{'':<11} "
              f"{llama_results['total_tokens']:>8.0f}{'':<11} "
              f"{total_diff:+.0f}")
        
        print()
        
        # Winner analysis
        print("🏆 Analysis:")
        if abs(acc_diff) < 1:
            print("  Accuracy: TIE (within 1%)")
        elif acc_diff > 0:
            print(f"  Accuracy: LLaMA wins by {acc_diff:.1f}%")
        else:
            print(f"  Accuracy: GPT-4o-mini wins by {abs(acc_diff):.1f}%")
        
        if token_pct < -5:
            print(f"  Tokens: LLaMA uses {abs(token_pct):.1f}% fewer tokens (more efficient)")
        elif token_pct > 5:
            print(f"  Tokens: GPT-4o-mini uses {token_pct:.1f}% fewer tokens (more efficient)")
        else:
            print("  Tokens: Similar usage")
        
        if lat_pct < -10:
            print(f"  Latency: LLaMA is {abs(lat_pct):.1f}% faster")
        elif lat_pct > 10:
            print(f"  Latency: GPT-4o-mini is {lat_pct:.1f}% faster")
        else:
            print("  Latency: Similar speed")
        
        print()
    
    print("="*80)
    print("CONCLUSION")
    print("="*80)
    print()
    print("Key Insights:")
    print("  • Both backends successfully run BAMoT experiments")
    print("  • Compare accuracy, token efficiency, and latency above")
    print("  • LLaMA provides local inference (no API costs)")
    print("  • GPT-4o-mini provides cloud inference (API costs)")
    print()

if __name__ == "__main__":
    compare_backends()

