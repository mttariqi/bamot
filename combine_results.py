#!/usr/bin/env python3
"""
Combine results from partial runs (e.g., 1-50 and 51-100) into full results.
This script merges CSV files and removes duplicates.
"""

import pandas as pd
import sys
from pathlib import Path

def combine_csvs(file1: str, file2: str, output: str):
    """Combine two CSV files, removing duplicates by ID."""
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)
    
    # Combine and remove duplicates (keep first occurrence)
    combined = pd.concat([df1, df2], ignore_index=True)
    combined = combined.drop_duplicates(subset=['id'], keep='first')
    combined = combined.sort_values('id')  # Sort by ID for consistency
    
    # Save combined results
    combined.to_csv(output, index=False)
    
    print(f"✅ Combined {len(df1)} + {len(df2)} = {len(combined)} unique items")
    print(f"   Saved to: {output}")
    
    return combined

def main():
    """Combine 50-item and 100-item results if needed."""
    results_dir = Path("results")
    
    # StrategyQA combinations
    if (results_dir / "bamot_sqa_50.csv").exists() and (results_dir / "bamot_sqa_100.csv").exists():
        print("Combining StrategyQA results...")
        combine_csvs(
            "results/bamot_sqa_50.csv",
            "results/bamot_sqa_100.csv",
            "results/bamot_sqa_full.csv"
        )
    
    # Game24 combinations
    for method in ["bamot", "tot", "got", "fot"]:
        file50 = results_dir / f"{method}_g24_50.csv"
        file100 = results_dir / f"{method}_g24_100.csv"
        
        if file50.exists() and file100.exists():
            print(f"Combining {method} Game24 results...")
            combine_csvs(
                str(file50),
                str(file100),
                f"results/{method}_g24_full.csv"
            )
    
    print("\n✅ All combinations complete!")

if __name__ == "__main__":
    main()

