#!/usr/bin/env python3
"""
Generate LaTeX tables from experiment results CSV files.
Usage: python scripts/generate_latex_tables.py
"""
import pandas as pd
import os
from pathlib import Path

def generate_table_latex(df, caption, label, dataset_filter=None, backend_filter='openai'):
    """Generate LaTeX table from DataFrame."""
    if dataset_filter:
        df = df[df['dataset'] == dataset_filter]
    if backend_filter:
        df = df[df['backend'] == backend_filter]
    
    # Filter to 100-item runs only
    df = df[df['total'] >= 100]
    
    # Select best BAMoT run (highest budget) and all baselines
    bamot_runs = df[df['method'] == 'bamot'].sort_values('mean_total_tokens', ascending=False)
    baselines = df[df['method'].isin(['cot', 'sc_cot', 'tot', 'got', 'fot'])]
    
    # Combine: best BAMoT + all baselines
    display_df = pd.concat([bamot_runs.head(1), baselines]).sort_values('accuracy', ascending=False)
    
    latex = "\\begin{table}[h]\n\\centering\n"
    latex += f"\\caption{{{caption}}}\n"
    latex += f"\\label{{{label}}}\n"
    latex += "\\begin{tabular}{lcccc}\n"
    latex += "\\toprule\n"
    latex += "Method & Accuracy (\\%) & Mean Tokens & Latency (s) & Source \\\\\n"
    latex += "\\midrule\n"
    
    for _, row in display_df.iterrows():
        method = row['method']
        if method == 'bamot' and row['mean_total_tokens'] > 300:
            method = f"BAMoT (budget {int(row['mean_total_tokens']*2.5):.0f})"
        else:
            method = method.upper()
        
        acc = row['accuracy'] * 100
        tokens = row['mean_total_tokens']
        latency = row['mean_latency']
        source = row.get('source', 'N/A').replace('_', '\\_')
        
        latex += f"{method} & {acc:.1f} & {tokens:.1f} & {latency:.2f} & {source} \\\\\n"
    
    latex += "\\bottomrule\n"
    latex += "\\end{tabular}\n"
    latex += "\\end{table}\n"
    
    return latex

def main():
    """Generate LaTeX tables for all datasets."""
    base_dir = Path(__file__).parent.parent
    summary_csv = base_dir / 'results' / 'summary_snapshot_20251117.csv'
    
    if not summary_csv.exists():
        print(f"Error: {summary_csv} not found. Run the summary generation script first.")
        return
    
    df = pd.read_csv(summary_csv)
    
    tables_dir = base_dir / 'thesis' / 'tables'
    tables_dir.mkdir(exist_ok=True)
    
    datasets = ['game24', 'strategyqa', 'gsm8k', 'math500']
    
    for dataset in datasets:
        if dataset not in df['dataset'].values:
            continue
        
        latex = generate_table_latex(
            df,
            caption=f"Performance comparison on {dataset.upper()} (GPT-4o-mini)",
            label=f"tab:{dataset}",
            dataset_filter=dataset,
            backend_filter='openai'
        )
        
        output_file = tables_dir / f"table_{dataset}.tex"
        with open(output_file, 'w') as f:
            f.write(latex)
        
        print(f"Generated: {output_file}")
    
    print("\n✅ LaTeX tables generated in thesis/tables/")
    print("Include them in your chapters with: \\input{tables/table_<dataset>.tex}")

if __name__ == '__main__':
    main()

