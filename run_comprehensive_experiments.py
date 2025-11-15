#!/usr/bin/env python3
"""
Comprehensive experiment runner for all methods across multiple datasets.
Runs BAMoT, CoT, SC-CoT, ToT, GoT, FoT on Game24, StrategyQA, GSM8K, MATH-500
"""
import subprocess
import sys
import os
from datetime import datetime

def run_experiment(method, dataset, budget, seeds=None, **kwargs):
    """Run a single experiment."""
    cmd = [
        "python3", "run.py",
        "--method", method,
        "--dataset", dataset,
        "--budget_tokens", str(budget),
        "--limit", "20",  # 20 items per experiment
    ]
    
    if method == "bamot":
        cmd.extend(["--seeds", str(seeds or 2)])
        cmd.extend(["--bamot_seed_tokens", "80"])
        cmd.extend(["--bamot_refine_tokens", "256"])
    elif method == "sc_cot":
        cmd.extend(["--sc_samples", str(seeds or 5)])
    elif method == "tot":
        cmd.extend(["--tot_branch", "2"])
        cmd.extend(["--tot_depth", "2"])
    elif method == "got":
        cmd.extend(["--got_beam", "2"])
        cmd.extend(["--got_steps", "2"])
    elif method == "fot":
        cmd.extend(["--fot_trees", "3"])
        cmd.extend(["--fot_branch", "2"])
        cmd.extend(["--fot_depth", "1"])
    
    # Add experiment name
    exp_name = f"{method}_{dataset}_B{budget}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    cmd.extend(["--exp_name", exp_name])
    
    print(f"\n{'='*70}")
    print(f"Running: {method} on {dataset} (budget={budget})")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*70}\n")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Success: {method} on {dataset}")
        # Extract accuracy from output
        if "Accuracy:" in result.stdout:
            print(result.stdout.split("Accuracy:")[-1].split("\n")[0])
    else:
        print(f"❌ Error: {method} on {dataset}")
        print(result.stderr)
    
    return result.returncode == 0

def main():
    """Run comprehensive experiments."""
    print("="*70)
    print("COMPREHENSIVE BAMoT EXPERIMENTS")
    print("="*70)
    print(f"Start time: {datetime.now()}")
    print()
    
    # Experiment configuration
    budgets = [1200, 1800, 2400]
    datasets = ["game24", "strategyqa", "gsm8k", "math500"]
    methods = ["bamot", "cot", "sc_cot", "tot", "got", "fot"]
    
    results = []
    
    # Run experiments
    for dataset in datasets:
        for budget in budgets:
            for method in methods:
                try:
                    success = run_experiment(method, dataset, budget)
                    results.append({
                        "method": method,
                        "dataset": dataset,
                        "budget": budget,
                        "success": success
                    })
                except Exception as e:
                    print(f"❌ Exception: {method} on {dataset} at B={budget}: {e}")
                    results.append({
                        "method": method,
                        "dataset": dataset,
                        "budget": budget,
                        "success": False
                    })
    
    # Summary
    print("\n" + "="*70)
    print("EXPERIMENT SUMMARY")
    print("="*70)
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"Successful: {successful}/{total}")
    print(f"Failed: {total - successful}/{total}")
    print(f"End time: {datetime.now()}")
    print()
    print("Next: Run 'python3 analyze_results.py' to generate comparison tables")

if __name__ == "__main__":
    main()

