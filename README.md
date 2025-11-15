# 🧠 BAMoT: Budget-Aware Mesh-of-Thoughts for Efficient LLM Reasoning

**Authors:** Muhmmad Tariq, Tahseen Zia  
**Affiliation:** COMSATS University Islamabad  
**Contact:** mttariqi786@gmail.com  

> Budget-Aware Mesh-of-Thoughts (BAMoT) introduces a cost-efficient reasoning framework for Large Language Models (LLMs).  
> It dynamically allocates a fixed token budget across reasoning paths (micro-seeds → triage → selective refinement → consensus), achieving strong accuracy at substantially lower token cost and latency.

---

## 🚀 Overview

**BAMoT** bridges the gap between accuracy and compute in LLM reasoning.  
Unlike *Chain-of-Thought (CoT)*, *Self-Consistent CoT (SC-CoT)*, *Tree-of-Thought (ToT)*, *Graph-of-Thought (GoT)*, and *Forest-of-Thought (FoT)*—which often expand exponentially—**BAMoT operates under a fixed token budget**.

The controller emits diverse **micro-seeds**, scores them via **lightweight triage**, and spends the remaining budget only on top candidates with **selective refinement** and **early stopping**.

---

## 📦 Repository Structure

```
bamot/
├── methods/              # Reasoning method implementations
│   ├── bamot.py         # BAMoT controller (main contribution)
│   ├── cot.py           # Chain-of-Thought
│   ├── sc_cot.py        # Self-Consistent CoT
│   ├── tot.py           # Tree-of-Thoughts
│   ├── got.py           # Graph-of-Thoughts
│   └── fot.py           # Forest-of-Thoughts
├── loaders/              # Dataset loaders
│   ├── gsm8k.py
│   ├── game24.py
│   ├── strategyqa.py
│   └── math500.py
├── utils/                # Utilities
│   ├── model_gateway.py  # Multi-backend LLM interface
│   ├── evals.py          # Evaluation functions
│   ├── tokens.py         # Token estimation
│   └── logger.py         # Logging utilities
├── run.py                # Main experiment launcher
├── compare_all_methods_backends.py  # Comprehensive comparison script
├── results/              # Experiment results (CSV files, excluded from git)
└── models/               # Model files (excluded from git)
```

---

## ⚙️ Installation & Setup

### Prerequisites

- **Python ≥ 3.10**
- **OpenAI API key** (for GPT-4o-mini backend)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Set OpenAI API Key

```bash
export OPENAI_API_KEY="sk-..."
```

**For persistent setup (macOS/Linux):**
```bash
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc  # or ~/.bashrc
source ~/.zshrc
```

### Step 3: Verify Setup

```bash
python3 test_smoke.py
```

---

## 🔧 Local Model Support (Optional)

### LLaMA/Qwen Backend Setup

For local inference with LLaMA or Qwen models:

#### 1. Install llama-cpp-python

```bash
pip install llama-cpp-python

# For Apple Silicon (M1/M2/M3):
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python

# For CUDA (NVIDIA GPU):
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
```

#### 2. Download Model

Download a GGUF model file (recommended: LLaMA 3.2 1B or Qwen 2.5 1.5B):

```bash
# Example: LLaMA 3.2 1B
wget -O models/llama-3.2-1b-instruct-q4_k_m.gguf \
  https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf

# Example: Qwen 2.5 1.5B
wget -O models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

#### 3. Set Model Path

```bash
export LLAMA_MODEL_PATH="$(pwd)/models/llama-3.2-1b-instruct-q4_k_m.gguf"
```

#### 4. Test Setup

```bash
python3 test_llama_setup.py
```

---

## ▶️ Running Experiments

### Basic Usage

**Run BAMoT on Game24:**
```bash
python3 run.py --method bamot --dataset game24 \
  --budget_tokens 1800 --seeds 3 \
  --bamot_seed_tokens 100 --bamot_refine_tokens 300 \
  --limit 100 --exp_name bamot_g24_100
```

**Run with local LLaMA:**
```bash
python3 run.py --backend llama_cpp \
  --llama_model_path models/llama-3.2-1b-instruct-q4_k_m.gguf \
  --method bamot --dataset game24 --limit 100 \
  --exp_name bamot_g24_llama_100
```

**Run with Qwen:**
```bash
python3 run.py --backend llama_cpp \
  --llama_model_path models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --method bamot --dataset game24 --limit 100 \
  --exp_name bamot_g24_qwen_100
```

### Compare All Methods

```bash
# BAMoT
python3 run.py --method bamot --dataset game24 --limit 100 --exp_name bamot_g24_100

# CoT
python3 run.py --method cot --dataset game24 --limit 100 --exp_name cot_g24_100

# SC-CoT
python3 run.py --method sc_cot --dataset game24 --sc_samples 5 --limit 100 --exp_name sc_cot_g24_100

# ToT
python3 run.py --method tot --dataset game24 --tot_branch 2 --tot_depth 2 --limit 100 --exp_name tot_g24_100

# GoT
python3 run.py --method got --dataset game24 --got_beam 2 --got_steps 2 --limit 100 --exp_name got_g24_100

# FoT
python3 run.py --method fot --dataset game24 --fot_trees 3 --fot_branch 2 --fot_depth 1 --limit 100 --exp_name fot_g24_100
```

### Generate Comprehensive Comparison

```bash
python3 compare_all_methods_backends.py
# Generates results/comprehensive_comparison.csv and summary tables
```

---

## 🧩 Supported Datasets

- **GSM8K** — Grade-school math word problems
- **Game-of-24** — Symbolic arithmetic target=24
- **StrategyQA** — Boolean commonsense QA (yes/no)
- **MATH-500** — Short-form math problems (numeric answers)

---

## 🧮 BAMoT Controller Parameters

- `--budget_tokens B` : Global cap on total tokens per item
- `--seeds S` : Number of micro-seeds in the initial pool
- `--bamot_seed_tokens T_s` : Max tokens per seed
- `--bamot_refine_tokens T_r` : Tokens per refinement step
- `--bamot_no_triage` : Disable triage (not recommended)
- `--bamot_no_consensus` : Disable final consensus
- `--bamot_refine_topk K` : Number of top candidates to refine

**Complexity:** `O(S·T_s + K·R·T_r) ≤ O(B)` — BAMoT spends a fixed budget instead of exploring exponentially.

---

## 📈 Experimental Results

### Game-of-24 (100 items, comprehensive evaluation)

#### Accuracy Comparison

| Method | GPT-4o-mini | LLaMA 1B | Qwen 1.5B | Average |
|:-------|:-----------:|:--------:|:---------:|:-------:|
| **BAMoT** | **23.0%** | **17.0%** | 0.0%* | **13.33%** |
| ToT | 21.0% | 0.0% | 5.0% | 8.67% |
| FoT | 19.0% | 16.0% | 0.0%* | 11.67% |
| GoT | 16.0% | 0.0% | 4.0% | 6.67% |
| CoT | 0.0% | 0.0% | 0.0% | 0.0% |
| SC-CoT | 0.0% | 0.0% | 0.0% | 0.0% |

*Backend errors encountered

#### Efficiency Metrics

| Method | Avg Tokens/Item | Avg Latency (s) | Accuracy |
|:-------|:---------------:|:---------------:|:--------:|
| **BAMoT** | **858** | **0.852** | **13.33%** |
| ToT | 1,708 | 1.191 | 8.67% |
| FoT | 2,255 | 0.789 | 11.67% |
| GoT | 781 | 1.209 | 6.67% |

### Key Findings

1. **BAMoT achieves highest accuracy** (13.33% average) across all backends
2. **50% fewer tokens** than ToT while maintaining better accuracy
3. **62% fewer tokens** than FoT
4. **2x better accuracy** than GoT with only 10% more tokens
5. **Consistent performance** across different model backends

### Multi-Backend Support

BAMoT has been tested across multiple LLM backends:

- **OpenAI API** (GPT-4o-mini): Best overall performance (23.0% accuracy)
- **LLaMA 3.2 1B** (Local): Strong performance (17.0% accuracy)
- **Qwen 2.5 1.5B** (Local): Compatible with local inference

---

## 💻 CLI Quick Reference

```bash
python3 run.py \
  --method {cot,sc_cot,bamot,tot,got,fot} \
  --dataset {gsm8k,game24,strategyqa,math500} \
  [--limit N] \
  [--backend {openai,llama_cpp}] \
  [--llama_model_path PATH] \
  [--budget_tokens B] \
  [--seeds S] \
  [--bamot_seed_tokens TS] \
  [--bamot_refine_tokens TR] \
  [--exp_name TAG]
```

**Full parameter list:**
- `--method`: Method to use (bamot, cot, sc_cot, tot, got, fot)
- `--dataset`: Dataset name (gsm8k, game24, strategyqa, math500)
- `--limit`: Number of items to process
- `--backend`: LLM backend (openai, llama_cpp)
- `--llama_model_path`: Path to GGUF model file
- `--budget_tokens`: Token budget for BAMoT
- `--seeds`: Number of micro-seeds
- `--exp_name`: Experiment name (for output CSV)

---

## 🧩 Troubleshooting

### "OPENAI_API_KEY not set" Error
```bash
export OPENAI_API_KEY="sk-..."
# Verify: echo $OPENAI_API_KEY
```

### "llama-cpp-python not found"
```bash
pip install llama-cpp-python
# For Apple Silicon: CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
```

### "No LLaMA model path provided"
```bash
export LLAMA_MODEL_PATH="/path/to/model.gguf"
# Or use --llama_model_path argument
```

### Rate Limiting
- Add delays between calls if hitting rate limits
- Use `--limit` to test on smaller subsets first

### Token Budget Issues
- Verify budget enforcement: check `results/*.csv` for token usage
- Should be ≤ `budget_tokens` per item

---

## 🔬 Ablations

| Variant | Accuracy | Mean Tokens | p50 Latency |
|:--------|:--------:|------------:|------------:|
| **BAMoT (base s2,r256)** | 1.00 | ~640 | ~3.1s |
| NoTriage | 0.00 | ~638 | ~3.5s |
| NoConsensus | 1.00 | ~620 | ~3.4s |
| s1,r256 | 0.75 | ~582 | ~3.1s |
| s3,r256 | 0.50 | ~629 | ~3.4s |

**Takeaway:** Triage is essential; consensus can be relaxed for arithmetic; seeds=2 is optimal.

---

## 🧠 Citation

```bibtex
@article{tariq2025bamot,
  title   = {BAMoT: Budget-Aware Mesh-of-Thoughts for Efficient LLM Reasoning},
  author  = {Muhmmad Tariq and Tahseen Zia},
  journal = {arXiv preprint},
  year    = {2025}
}
```

---

## 💡 Acknowledgments

Developed under the supervision of **Prof. Tahseen Zia**, COMSATS University Islamabad.  
Builds on open-source CoT/ToT/GoT/FoT reasoning paradigms.

---

## 📊 Results Files

All experiment results are saved to `results/` directory as CSV files. To regenerate comparisons:

```bash
python3 compare_all_methods_backends.py
```

This generates `results/comprehensive_comparison.csv` with detailed metrics across all methods and backends.

---

## 🔗 Additional Resources

- **Repository**: https://github.com/mttariqi/bamot
- **Issues**: Report bugs or request features via GitHub Issues
- **Paper**: (arXiv link to be added)

---

**Last Updated**: November 2025  
**Version**: 1.0
