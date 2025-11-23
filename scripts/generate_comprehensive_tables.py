#!/usr/bin/env python3
"""
Generate comprehensive LaTeX tables and figures from experiment results.
"""
import pandas as pd
import csv
from pathlib import Path
import glob
import os

def load_csv_results(filepath):
    """Load results from CSV file."""
    if not os.path.exists(filepath):
        return None
    
    try:
        df = pd.read_csv(filepath)
        if len(df) == 0:
            return None
        
        # Standardize column names
        if 'correct' in df.columns:
            df['correct'] = df['correct'].astype(str).str.strip()
            df['correct'] = df['correct'].isin(['1', 'True', 'true', 'TRUE', '1.0']).astype(int)
        
        return df
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def compute_metrics(df, method_name, dataset, backend):
    """Compute metrics from DataFrame."""
    if df is None or len(df) == 0:
        return None
    
    # Filter out error rows
    if 'pred' in df.columns:
        df = df[~df['pred'].astype(str).str.startswith('ERROR:', na=False)]
    
    if len(df) == 0:
        return None
    
    total = len(df)
    correct = int(df['correct'].sum()) if 'correct' in df.columns else 0
    accuracy = (correct / total * 100) if total > 0 else 0.0
    
    # Token usage
    if 'prompt_toks' in df.columns and 'completion_toks' in df.columns:
        df['total_tokens'] = df['prompt_toks'].fillna(0) + df['completion_toks'].fillna(0)
        mean_tokens = df['total_tokens'].mean()
        total_tokens = df['total_tokens'].sum()
    elif 'tokens_used' in df.columns:
        mean_tokens = df['tokens_used'].mean()
        total_tokens = df['tokens_used'].sum()
    else:
        mean_tokens = 0.0
        total_tokens = 0
    
    # Latency
    if 'latency_sec' in df.columns:
        mean_latency = df['latency_sec'].mean()
    elif 'latency' in df.columns:
        mean_latency = df['latency'].mean()
    else:
        mean_latency = 0.0
    
    return {
        'method': method_name,
        'dataset': dataset,
        'backend': backend,
        'accuracy': accuracy,
        'correct': correct,
        'total': total,
        'mean_tokens': mean_tokens,
        'total_tokens': total_tokens,
        'mean_latency': mean_latency,
    }

def find_result_files():
    """Find all result CSV files."""
    results_dir = Path('results')
    files = []
    
    methods = ['bamot', 'cot', 'sc_cot', 'tot', 'got', 'fot']
    datasets = ['game24', 'gsm8k', 'math500', 'strategyqa']
    backends = {
        'openai': ['gpt4o-mini', 'openai'],
        'llama': ['llama'],
        'qwen': ['qwen']
    }
    
    for method in methods:
        for dataset in datasets:
            # OpenAI/GPT-4o-mini results
            pattern = f"{method}_{dataset}_100.csv"
            filepath = results_dir / pattern
            if filepath.exists():
                files.append((filepath, method, dataset, 'openai'))
            
            # Budget-specific BAMoT files
            if method == 'bamot':
                for budget in ['3200', '4800']:
                    pattern = f"{method}_{dataset}_budget{budget}_100.csv"
                    filepath = results_dir / pattern
                    if filepath.exists():
                        files.append((filepath, method, dataset, 'openai', budget))
            
            # Budget-specific baseline files
            if method in ['tot', 'got', 'fot']:
                pattern = f"{method}_{dataset}_budget800_100.csv"
                filepath = results_dir / pattern
                if filepath.exists():
                    files.append((filepath, method, dataset, 'openai', '800'))
            
            # LLaMA results
            pattern = f"{method}_{dataset}_llama_100.csv"
            filepath = results_dir / pattern
            if filepath.exists():
                files.append((filepath, method, dataset, 'llama'))
            
            # LLaMA budget-specific
            if method == 'bamot':
                pattern = f"{method}_{dataset}_llama_budget4800_100.csv"
                filepath = results_dir / pattern
                if filepath.exists():
                    files.append((filepath, method, dataset, 'llama', '4800'))
            
            # Qwen results
            pattern = f"{method}_{dataset}_qwen_100.csv"
            filepath = results_dir / pattern
            if filepath.exists():
                files.append((filepath, method, dataset, 'qwen'))
            
            # Qwen fixed results
            pattern = f"{method}_{dataset}_qwen_100_fixed.csv"
            filepath = results_dir / pattern
            if filepath.exists():
                files.append((filepath, method, dataset, 'qwen'))
            
            # Qwen budget-specific
            if method == 'bamot':
                pattern = f"{method}_{dataset}_qwen_budget4800_100.csv"
                filepath = results_dir / pattern
                if filepath.exists():
                    files.append((filepath, method, dataset, 'qwen', '4800'))
    
    return files

def generate_latex_table(results, dataset, backend='openai'):
    """Generate LaTeX table for a dataset and backend."""
    # Filter results
    filtered = [r for r in results if r and r['dataset'] == dataset and r['backend'] == backend]
    
    if not filtered:
        return None
    
    # Sort by accuracy descending
    filtered.sort(key=lambda x: x['accuracy'], reverse=True)
    
    # Method name mapping
    method_names = {
        'bamot': 'BAMoT',
        'cot': 'CoT',
        'sc_cot': 'SC-CoT',
        'tot': 'ToT',
        'got': 'GoT',
        'fot': 'FoT',
    }
    
    backend_names = {
        'openai': 'GPT-4o-mini',
        'llama': 'LLaMA 3.2 1B',
        'qwen': 'Qwen 2.5 1.5B',
    }
    
    latex = "\\begin{table}[h]\n"
    latex += "\\centering\n"
    latex += f"\\caption{{Performance comparison on {dataset.upper()} ({backend_names.get(backend, backend)})}}\n"
    latex += f"\\label{{tab:{dataset}_{backend}}}\n"
    latex += "\\begin{tabular}{lcccc}\n"
    latex += "\\toprule\n"
    latex += "Method & Accuracy (\\%) & Mean Tokens & Total Tokens & Latency (s) \\\\\n"
    latex += "\\midrule\n"
    
    for r in filtered:
        method = method_names.get(r['method'], r['method'].upper())
        # Add budget info for BAMoT if available
        if 'budget' in r and r['budget']:
            method = f"{method} (budget {r['budget']})"
        
        acc = r['accuracy']
        mean_tokens = r['mean_tokens']
        total_tokens = r['total_tokens']
        latency = r['mean_latency']
        
        latex += f"{method} & {acc:.1f} & {mean_tokens:.0f} & {total_tokens:.0f} & {latency:.2f} \\\\\n"
    
    latex += "\\bottomrule\n"
    latex += "\\end{tabular}\n"
    latex += "\\end{table}\n"
    
    return latex

def generate_comparison_table(results, dataset):
    """Generate comparison table across all backends for a dataset."""
    filtered = [r for r in results if r and r['dataset'] == dataset]
    
    if not filtered:
        return None
    
    # Get unique methods
    methods = sorted(set(r['method'] for r in filtered))
    
    # Method name mapping
    method_names = {
        'bamot': 'BAMoT',
        'cot': 'CoT',
        'sc_cot': 'SC-CoT',
        'tot': 'ToT',
        'got': 'GoT',
        'fot': 'FoT',
    }
    
    latex = "\\begin{table}[h]\n"
    latex += "\\centering\n"
    latex += f"\\caption{{Performance comparison across backends on {dataset.upper()}}}\n"
    latex += f"\\label{{tab:{dataset}_all_backends}}\n"
    latex += "\\resizebox{\\textwidth}{!}{%\n"
    latex += "\\begin{tabular}{lccccccc}\n"
    latex += "\\toprule\n"
    latex += "Method & \\multicolumn{2}{c}{GPT-4o-mini} & \\multicolumn{2}{c}{LLaMA} & \\multicolumn{2}{c}{Qwen} \\\\\n"
    latex += "\\cmidrule(lr){2-3} \\cmidrule(lr){4-5} \\cmidrule(lr){6-7}\n"
    latex += " & Acc. (\\%) & Tokens & Acc. (\\%) & Tokens & Acc. (\\%) & Tokens \\\\\n"
    latex += "\\midrule\n"
    
    for method in methods:
        method_display = method_names.get(method, method.upper())
        row = [method_display]
        
        for backend in ['openai', 'llama', 'qwen']:
            backend_results = [r for r in filtered if r['method'] == method and r['backend'] == backend]
            if backend_results:
                # Take best result (highest accuracy)
                best = max(backend_results, key=lambda x: x['accuracy'])
                row.append(f"{best['accuracy']:.1f}")
                row.append(f"{best['mean_tokens']:.0f}")
            else:
                row.append("--")
                row.append("--")
        
        latex += " & ".join(row) + " \\\\\n"
    
    latex += "\\bottomrule\n"
    latex += "\\end{tabular}%\n"
    latex += "}\n"
    latex += "\\end{table}\n"
    
    return latex

def main():
    """Generate all tables."""
    print("=" * 80)
    print("GENERATING LATEX TABLES FROM EXPERIMENT RESULTS")
    print("=" * 80)
    
    # Find all result files
    files = find_result_files()
    print(f"\nFound {len(files)} result files")
    
    # Load and compute metrics
    all_results = []
    for file_info in files:
        if len(file_info) == 4:
            filepath, method, dataset, backend = file_info
            budget = None
        else:
            filepath, method, dataset, backend, budget = file_info
        
        df = load_csv_results(filepath)
        if df is not None:
            metrics = compute_metrics(df, method, dataset, backend)
            if metrics:
                if budget:
                    metrics['budget'] = budget
                all_results.append(metrics)
                print(f"  ✓ {filepath.name}: {metrics['accuracy']:.1f}% accuracy, {metrics['mean_tokens']:.0f} tokens")
    
    if not all_results:
        print("\n❌ No results found. Check that CSV files exist in results/ directory.")
        return
    
    # Create tables directory
    tables_dir = Path('thesis/tables')
    tables_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate tables for each dataset and backend
    datasets = ['game24', 'gsm8k', 'math500', 'strategyqa']
    backends = ['openai', 'llama', 'qwen']
    
    print("\n" + "=" * 80)
    print("GENERATING LATEX TABLES")
    print("=" * 80)
    
    for dataset in datasets:
        for backend in backends:
            latex = generate_latex_table(all_results, dataset, backend)
            if latex:
                filename = f"table_{dataset}_{backend}.tex"
                filepath = tables_dir / filename
                with open(filepath, 'w') as f:
                    f.write(latex)
                print(f"  ✓ Generated: {filename}")
        
        # Also generate cross-backend comparison
        latex = generate_comparison_table(all_results, dataset)
        if latex:
            filename = f"table_{dataset}_comparison.tex"
            filepath = tables_dir / filename
            with open(filepath, 'w') as f:
                f.write(latex)
            print(f"  ✓ Generated: {filename}")
    
    print("\n" + "=" * 80)
    print("✅ ALL TABLES GENERATED SUCCESSFULLY")
    print("=" * 80)
    print(f"\nTables saved in: {tables_dir.absolute()}")
    print("\nInclude in your thesis with:")
    print("  \\input{tables/table_<dataset>_<backend>.tex}")
    print("  \\input{tables/table_<dataset>_comparison.tex}")

if __name__ == '__main__':
    main()

