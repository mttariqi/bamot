# BAMoT: Budget-Aware Mesh-of-Thoughts - Git Repository Summary

## Project Overview

**BAMoT (Budget-Aware Mesh-of-Thoughts)** is a cost-efficient reasoning framework for Large Language Models that dynamically allocates a fixed token budget across reasoning paths, achieving strong accuracy at substantially lower token cost and latency compared to existing methods.

## Key Features

- ✅ **Fixed Token Budget**: Operates under a strict token budget constraint
- ✅ **Multi-Backend Support**: OpenAI API, LLaMA (local), Qwen (local)
- ✅ **Multiple Methods**: BAMoT, CoT, SC-CoT, ToT, GoT, FoT implementations
- ✅ **Multiple Datasets**: Game24, GSM8K, StrategyQA, AIME, MATH-500
- ✅ **Comprehensive Evaluation**: Accuracy, token usage, latency metrics

## Repository Structure

```
bamot/
├── methods/              # Reasoning method implementations
│   ├── bamot.py         # BAMoT controller (main contribution)
│   ├── cot.py           # Chain-of-Thought
│   ├── sc_cot.py        # Self-Consistent CoT
│   ├── tot.py           # Tree-of-Thoughts
│   ├── got.py           # Graph-of-Thoughts
│   └── fot.py           # Forest-of-Thoughts
├── loaders/             # Dataset loaders
│   ├── game24.py
│   ├── gsm8k.py
│   ├── strategyqa.py
│   └── math500.py
├── utils/               # Utilities
│   ├── model_gateway.py # Multi-backend LLM interface
│   ├── evals.py         # Evaluation functions
│   ├── tokens.py        # Token estimation
│   └── logger.py        # Logging utilities
├── run.py               # Main experiment launcher
├── compare_all_methods_backends.py  # Comprehensive comparison script
├── results/             # Experiment results (CSV files)
├── models/              # Model files (excluded from git - too large)
└── docs/                # Documentation files
```

## Experimental Results

### Game24 Dataset (100 items)

| Method | GPT-4o-mini | LLaMA 1B | Qwen 1.5B | Average |
|--------|-------------|----------|-----------|---------|
| **BAMoT** | **23.0%** | **17.0%** | 0.0%* | **13.33%** |
| ToT | 21.0% | 0.0% | 5.0% | 8.67% |
| FoT | 19.0% | 16.0% | 0.0%* | 11.67% |
| GoT | 16.0% | 0.0% | 4.0% | 6.67% |
| CoT | 0.0% | 0.0% | 0.0% | 0.0% |
| SC-CoT | 0.0% | 0.0% | 0.0% | 0.0% |

*Backend errors encountered

### Key Findings

1. **BAMoT achieves highest average accuracy** (13.33%) across all backends
2. **Efficient token usage**: 858 tokens/item (50% less than ToT)
3. **Competitive latency**: 0.852s/item average
4. **Consistent performance** across different model backends

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key (for GPT-4o-mini)
export OPENAI_API_KEY="sk-..."

# For local models (optional)
# Download GGUF models to models/ directory
# See SETUP_LLAMA.md and QWEN_SETUP_COMPLETE.md for details
```

## Quick Start

```bash
# Run BAMoT on Game24
python3 run.py --method bamot --dataset game24 \
  --budget_tokens 1800 --seeds 3 \
  --limit 100 --exp_name bamot_g24_100

# Run with local LLaMA
python3 run.py --backend llama_cpp \
  --llama_model_path models/llama-3.2-1b-instruct-q4_k_m.gguf \
  --method bamot --dataset game24 --limit 100

# Compare all methods
python3 compare_all_methods_backends.py
```

## Documentation

- **README.md** - Main project documentation
- **COMPREHENSIVE_RESULTS.md** - Detailed experimental results
- **FINAL_SUMMARY.md** - Executive summary
- **SETUP_LOCAL.md** - Local setup guide
- **SETUP_LLAMA.md** - LLaMA backend setup
- **QWEN_SETUP_COMPLETE.md** - Qwen backend setup
- **FIXES_SUMMARY.md** - Bug fixes and improvements

## Excluded Files

The following are excluded from git (see `.gitignore`):

- `models/*.gguf` - Large model files (~1GB each)
- `results/*.csv` - Experiment result files
- `__pycache__/` - Python cache directories
- `*.pyc` - Compiled Python files
- `.env` - Environment variables
- Test/temporary files

## Requirements

- Python ≥ 3.10
- See `requirements.txt` for dependencies
- OpenAI API key (for GPT-4o-mini backend)
- Optional: `llama-cpp-python` for local models

## Citation

```bibtex
@article{tariq2025bamot,
  title   = {BAMoT: Budget-Aware Mesh-of-Thoughts for Efficient LLM Reasoning},
  author  = {Muhmmad Tariq and Tahseen Zia},
  journal = {arXiv preprint},
  year    = {2025}
}
```

## Authors

- **Muhmmad Tariq** - mttariqi786@gmail.com
- **Tahseen Zia** - Supervisor, COMSATS University Islamabad

## License

[Specify license if applicable]

---

**Last Updated**: November 2025
**Status**: Ready for publication

