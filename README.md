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

<p align="center">
  <img src="figures/bamot_pipeline.png" width="90%">
</p>

> **Fig. 1.** BAMoT pipeline — micro-seeds → triage → refine top-K under budget with early stop + consensus.

---

## 📦 Repository Structure

    bamot/
    ├── methods/
    │   ├── cot.py
    │   ├── sc_cot.py
    │   ├── tot.py
    │   ├── got.py
    │   ├── fot.py
    │   └── bamot.py              # ← BAMoT controller
    ├── loaders/
    │   ├── gsm8k.py
    │   ├── game24.py
    │   ├── strategyqa.py
    │   ├── aime.py
    │   └── math500.py
    ├── utils/
    │   ├── model_gateway.py
    │   ├── tokens.py
    │   ├── logger.py
    │   └── evals.py
    ├── prompts/
    │   ├── cot_prompt.txt
    │   └── answer_extract.txt
    ├── data/                     # (optional local caches)
    │   ├── gsm8k/      test.jsonl
    │   ├── game24/     test.jsonl
    │   ├── strategyqa/ dev.jsonl
    │   ├── aime/       dev.jsonl
    │   └── math500/    dev.jsonl
    ├── results/                  # CSV outputs auto-saved here
    ├── figures/                  # plots exported here
    ├── run.py                    # main launcher
    ├── plot_results.py           # plotting / AUC / summaries
    └── README.md

---

## ⚙️ Installation & Requirements

- **Python ≥ 3.10**  
- **Recommended:** Google Colab (A100) or local GPU (optional; API usage is the bottleneck)

Install dependencies:

    pip install -r requirements.txt

### Optional: Local Model Support

For local LLaMA/Qwen models:

    # Install llama-cpp-python
    pip install llama-cpp-python
    
    # For Apple Silicon (M1/M2/M3)
    CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python

Set your OpenAI API key (for GPT-4o-mini):

    export OPENAI_API_KEY="sk-..."     # required

---

## ▶️ Running Experiments

**Single run (example):**

    python3 run.py --method bamot --dataset game24 \
      --budget_tokens 1800 --seeds 2 \
      --bamot_seed_tokens 80 --bamot_refine_tokens 256 \
      --exp_name bamot_g24_B1800

**Run with local models:**

    # LLaMA
    python3 run.py --backend llama_cpp \
      --llama_model_path models/llama-3.2-1b-instruct-q4_k_m.gguf \
      --method bamot --dataset game24 --limit 100

    # Qwen
    python3 run.py --backend llama_cpp \
      --llama_model_path models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
      --method bamot --dataset game24 --limit 100

**Compare baselines under a matched budget:**

    # CoT
    python3 run.py --method cot --dataset game24 --limit 100

    # SC-CoT
    python3 run.py --method sc_cot --dataset game24 --sc_samples 5 --limit 100

    # ToT / GoT / FoT
    python3 run.py --method tot --dataset game24 --tot_branch 2 --tot_depth 2 --limit 100
    python3 run.py --method got --dataset game24 --got_beam 2 --got_steps 2 --limit 100
    python3 run.py --method fot --dataset game24 --fot_trees 3 --fot_branch 2 --fot_depth 1 --limit 100

**Generate comprehensive comparison:**

    python3 compare_all_methods_backends.py
    # Generates results/comprehensive_comparison.csv and summary tables

---

## 🧩 Datasets

- **GSM8K** — Grade-school math word problems  
- **Game-of-24** — Symbolic arithmetic target=24  
- **StrategyQA** — Boolean commonsense QA (yes/no)  
- **AIME** — Competition-style math (numeric answers)  
- **MATH-500** — Short-form math problems (numeric answers)

> Place small dev/test JSONL files under `data/<dataset>/` if you want fully offline runs.  
> Otherwise, loaders will use minimal built-in samples or fetch known-lite splits where supported.

---

## 🧮 BAMoT Controller (Key Params)

- `--budget_tokens B` : **Global** cap on total tokens per item (prompt + completions across all candidates)  
- `--seeds S` : number of **micro-seeds** (short chains) in the initial pool  
- `--bamot_seed_tokens T_s` : max tokens per seed  
- `--bamot_refine_tokens T_r` : tokens per **refinement** step for selected candidates  
- `--bamot_no_triage` : disable triage (not recommended)  
- `--bamot_no_consensus` : disable final consensus (can help arithmetic edge cases)  

Early stopping via task verifiers (exact number match, 24-check, yes/no normalizer).

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

**Key Findings:**
- BAMoT achieves **highest accuracy** (13.33% average)
- Uses **50% fewer tokens** than ToT while maintaining better accuracy
- **62% fewer tokens** than FoT
- **2x better accuracy** than GoT with only 10% more tokens

### Multi-Backend Support

BAMoT has been tested across multiple LLM backends:

- **OpenAI API** (GPT-4o-mini): Best overall performance
- **LLaMA 3.2 1B** (Local): Strong performance, demonstrates method robustness
- **Qwen 2.5 1.5B** (Local): Compatible with local inference

See `SETUP_LLAMA.md` and `QWEN_SETUP_COMPLETE.md` for local model setup.

> 📊 **Full results available in**: `COMPREHENSIVE_RESULTS.md` and `results/comprehensive_comparison.csv`

---

## 🔬 Ablations (MATH-500, B=600)

| Variant                  |  Acc | Mean Tokens | p50 Latency |
|:-------------------------|:----:|------------:|------------:|
| **BAMoT (base s2,r256)** | 1.00 |     ~640    |    ~3.1s    |
| NoTriage (s2,r256)       | 0.00 |     ~638    |    ~3.5s    |
| NoConsensus (s2,r256)    | 1.00 |     ~620    |    ~3.4s    |
| s1,r256                  | 0.75 |     ~582    |    ~3.1s    |
| s3,r256                  | 0.50 |     ~629    |    ~3.4s    |
| s2,r320                  | 1.00 |     ~636    |    ~3.7s    |

**Takeaway:** triage is essential; consensus can be relaxed for arithmetic; seeds=2 is a sweet spot.

---

## 🧮 Theory → Practice

BAMoT keeps compute **linear in budget**: `O(S·T_s + K·R·T_r) ≤ O(B)`  
and empirically tracks budget ≈ tokens-used (near-unit slope). Accuracy rises **sub-linearly** with budget and saturates, showing diminishing returns—perfect for **anytime** use.

<p align="center">
  <img src="figures/efficiency_scaling.png" width="78%">
  <br><em>Fig. 2. Total tokens grow ~linearly with budget B.</em>
</p>

<p align="center">
  <img src="figures/accuracy_budget_curve.png" width="78%">
  <br><em>Fig. 3. Accuracy vs budget shows graceful improvement and early saturation.</em>
</p>

---

## 💻 CLI Quick Reference

    python run.py --method {cot,sc_cot,bamot,tot,got,fot} \
                  --dataset {gsm8k,game24,strategyqa,aime,math500} \
                  [--limit N] \
                  [--model NAME] \
                  [--temperature T] \
                  [--max_tokens N] \
                  [--budget_tokens B] \
                  [--seeds S] \
                  [--sc_samples K] \
                  [--exp_name TAG] \
                  [--bamot_no_triage] [--bamot_no_consensus] \
                  [--bamot_seed_tokens TS] [--bamot_refine_tokens TR] \
                  [--bamot_early_stop_gold] [--bamot_gold_value V] \
                  [--tot_branch B] [--tot_depth D] \
                  [--got_beam K] [--got_steps R] \
                  [--fot_trees F] [--fot_branch B] [--fot_depth D]

- **Budgeted baselines:** tune branch/depth/beam/steps to fit the same `--budget_tokens`.  
- **Reproducibility:** use `--exp_name` to snapshot CSVs into `./results/`.

---

## 🧩 Troubleshooting

- **“invalid choice: 'gsm8k_fot'”**  
  Use `--dataset gsm8k` (not `gsm8k_fot`). If you drop FoT-style JSONL files, keep the dataset name unchanged; place files under `data/gsm8k/test.jsonl` (or adapt loader).

- **“SyntaxError: for B in ...” in Python**  
  Bash for-loops go in **shell**, not Python. Use a shell cell or wrap with `subprocess` if needed.

- **Latency spikes in tree methods**  
  Reduce `--tot_depth / --fot_depth` or beams; keep **budget parity** with BAMoT for fair comparisons.

---

## 🧠 Citation

    @article{tariq2025bamot,
      title   = {BAMoT: Budget-Aware Mesh-of-Thoughts for Efficient LLM Reasoning},
      author  = {Muhmmad Tariq and Tahseen Zia},
      journal = {arXiv preprint arXiv:XXXX.XXXXX},
      year    = {2025}
    }

---

## 💡 Acknowledgments
Developed under the supervision of **Prof. Tahseen Zia**, COMSATS University Islamabad.  
Builds on open-source CoT/ToT/GoT/FoT reasoning paradigms.

---

<!-- Optional links -->
<!-- [📄 Paper (arXiv)](https://arxiv.org/abs/XXXX.XXXXX) -->
<!-- [🧪 Colab Demo](https://colab.research.google.com/) -->
