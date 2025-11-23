#!/usr/bin/env python3
"""
Generate figures/visualizations from experiment results.
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import glob
import os

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'serif'

def load_csv_results(filepath):
    """Load results from CSV file."""
    if not os.path.exists(filepath):
        return None
    
    try:
        df = pd.read_csv(filepath)
        if len(df) == 0:
            return None
        
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
    
    if 'pred' in df.columns:
        df = df[~df['pred'].astype(str).str.startswith('ERROR:', na=False)]
    
    if len(df) == 0:
        return None
    
    total = len(df)
    correct = int(df['correct'].sum()) if 'correct' in df.columns else 0
    accuracy = (correct / total * 100) if total > 0 else 0.0
    
    if 'prompt_toks' in df.columns and 'completion_toks' in df.columns:
        df = df.copy()
        df['total_tokens'] = df['prompt_toks'].fillna(0) + df['completion_toks'].fillna(0)
        mean_tokens = df['total_tokens'].mean()
    elif 'tokens_used' in df.columns:
        mean_tokens = df['tokens_used'].mean()
    else:
        mean_tokens = 0.0
    
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
        'mean_tokens': mean_tokens,
        'mean_latency': mean_latency,
    }

def find_result_files():
    """Find all result CSV files."""
    results_dir = Path('results')
    files = []
    
    methods = ['bamot', 'cot', 'sc_cot', 'tot', 'got', 'fot']
    datasets = ['game24', 'gsm8k', 'math500', 'strategyqa']
    
    for method in methods:
        for dataset in datasets:
            # OpenAI results
            pattern = f"{method}_{dataset}_100.csv"
            filepath = results_dir / pattern
            if filepath.exists():
                files.append((filepath, method, dataset, 'openai'))
            
            # Budget-specific BAMoT
            if method == 'bamot':
                for budget in ['3200', '4800']:
                    pattern = f"{method}_{dataset}_budget{budget}_100.csv"
                    filepath = results_dir / pattern
                    if filepath.exists():
                        files.append((filepath, method, dataset, 'openai', budget))
            
            # LLaMA results
            pattern = f"{method}_{dataset}_llama_100.csv"
            filepath = results_dir / pattern
            if filepath.exists():
                files.append((filepath, method, dataset, 'llama'))
            
            # Qwen results
            pattern = f"{method}_{dataset}_qwen_100.csv"
            filepath = results_dir / pattern
            if filepath.exists():
                files.append((filepath, method, dataset, 'qwen'))
            
            pattern = f"{method}_{dataset}_qwen_100_fixed.csv"
            filepath = results_dir / pattern
            if filepath.exists():
                files.append((filepath, method, dataset, 'qwen'))
    
    return files

def plot_accuracy_vs_tokens(results, dataset, output_dir):
    """Plot accuracy vs token usage."""
    filtered = [r for r in results if r and r['dataset'] == dataset and r['backend'] == 'openai']
    
    if not filtered:
        return None
    
    # Method name mapping
    method_names = {
        'bamot': 'BAMoT',
        'cot': 'CoT',
        'sc_cot': 'SC-CoT',
        'tot': 'ToT',
        'got': 'GoT',
        'fot': 'FoT',
    }
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for r in filtered:
        method = method_names.get(r['method'], r['method'].upper())
        if 'budget' in r and r.get('budget'):
            method = f"{method} (B={r['budget']})"
        
        ax.scatter(r['mean_tokens'], r['accuracy'], 
                  s=150, alpha=0.7, label=method)
    
    ax.set_xlabel('Mean Tokens per Instance', fontsize=12)
    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_title(f'Accuracy vs Token Usage: {dataset.upper()} (GPT-4o-mini)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    
    plt.tight_layout()
    filename = output_dir / f"figure_{dataset}_accuracy_tokens.pdf"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return filename

def plot_backend_comparison(results, dataset, output_dir):
    """Plot comparison across backends."""
    filtered = [r for r in results if r and r['dataset'] == dataset]
    
    if not filtered:
        return None
    
    # Get methods
    methods = sorted(set(r['method'] for r in filtered))
    backends = ['openai', 'llama', 'qwen']
    backend_labels = ['GPT-4o-mini', 'LLaMA', 'Qwen']
    
    method_names = {
        'bamot': 'BAMoT',
        'cot': 'CoT',
        'sc_cot': 'SC-CoT',
        'tot': 'ToT',
        'got': 'GoT',
        'fot': 'FoT',
    }
    
    # Prepare data
    data = []
    for method in methods:
        for backend in backends:
            backend_results = [r for r in filtered if r['method'] == method and r['backend'] == backend]
            if backend_results:
                best = max(backend_results, key=lambda x: x['accuracy'])
                data.append({
                    'Method': method_names.get(method, method.upper()),
                    'Backend': backend_labels[backends.index(backend)],
                    'Accuracy': best['accuracy']
                })
    
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create grouped bar chart
    methods_unique = df['Method'].unique()
    x = range(len(methods_unique))
    width = 0.25
    
    for i, backend in enumerate(backend_labels):
        backend_data = df[df['Backend'] == backend]
        accuracies = [backend_data[backend_data['Method'] == m]['Accuracy'].values[0] 
                     if len(backend_data[backend_data['Method'] == m]) > 0 else 0 
                     for m in methods_unique]
        ax.bar([xi + i*width for xi in x], accuracies, width, label=backend, alpha=0.8)
    
    ax.set_xlabel('Method', fontsize=12)
    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_title(f'Accuracy Comparison Across Backends: {dataset.upper()}', fontsize=14, fontweight='bold')
    ax.set_xticks([xi + width for xi in x])
    ax.set_xticklabels(methods_unique, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    filename = output_dir / f"figure_{dataset}_backend_comparison.pdf"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return filename

def main():
    """Generate all figures."""
    print("=" * 80)
    print("GENERATING FIGURES FROM EXPERIMENT RESULTS")
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
    
    if not all_results:
        print("\n❌ No results found.")
        return
    
    # Create figures directory
    figures_dir = Path('thesis/figures')
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 80)
    print("GENERATING FIGURES")
    print("=" * 80)
    
    datasets = ['gsm8k', 'math500']
    
    for dataset in datasets:
        # Accuracy vs tokens
        filename = plot_accuracy_vs_tokens(all_results, dataset, figures_dir)
        if filename:
            print(f"  ✓ Generated: {filename.name}")
        
        # Backend comparison
        filename = plot_backend_comparison(all_results, dataset, figures_dir)
        if filename:
            print(f"  ✓ Generated: {filename.name}")
    
    print("\n" + "=" * 80)
    print("✅ ALL FIGURES GENERATED SUCCESSFULLY")
    print("=" * 80)
    print(f"\nFigures saved in: {figures_dir.absolute()}")
    print("\nInclude in your thesis with:")
    print("  \\begin{figure}[h]")
    print("    \\centering")
    print("    \\includegraphics[width=0.8\\textwidth]{figures/figure_<name>.pdf}")
    print("    \\caption{Your caption}")
    print("    \\label{fig:<label>}")
    print("  \\end{figure}")

if __name__ == '__main__':
    main()

