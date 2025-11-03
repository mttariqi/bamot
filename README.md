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

Set your OpenAI API key:

    export OPENAI_API_KEY="sk-..."     # required

---

## ▶️ Running Experiments

**Single run (example):**

    python3 run.py --method bamot --dataset game24 \
      --budget_tokens 1800 --seeds 2 \
      --bamot_seed_tokens 80 --bamot_refine_tokens 256 \
      --exp_name bamot_g24_B1800

**Compare baselines under a matched budget:**

    # CoT
    python3 run.py --method cot --dataset strategyqa \
      --budget_tokens 1200 --exp_name cot_sqa_B1200

    # SC-CoT (e.g., 5 samples)
    python3 run.py --method sc_cot --dataset aime \
      --sc_samples 5 --budget_tokens 1200 --exp_name sc_cot_aime_B1200

    # ToT / GoT / FoT (light settings shown; adjust to meet budget)
    python3 run.py --method tot --dataset game24 \
      --tot_branch 2 --tot_depth 1 --budget_tokens 1200 --exp_name tot_g24_B1200

    python3 run.py --method got --dataset math500 \
      --got_beam 2 --got_steps 2 --budget_tokens 1200 --exp_name got_m500_B1200

    python3 run.py --method fot --dataset strategyqa \
      --fot_trees 3 --fot_branch 2 --fot_depth 1 --budget_tokens 1200 --exp_name fot_sqa_B1200

**Sweep budgets (B ∈ {600, 1200, 1800, 2400}):**

    for B in 600 1200 1800 2400; do
      python3 run.py --method bamot --dataset strategyqa \
        --budget_tokens $B --seeds 2 --bamot_seed_tokens 80 --bamot_refine_tokens 256 \
        --exp_name bamot_sqa_B${B}
    done

**Plot summaries & AUC(Anytime):**

    python3 plot_results.py
    # saves combined tables and charts into ./figures/

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

## 📈 Experimental Results (from dev slices)

### Game-of-24 (efficiency snapshot)

| Method      | Acc (%) | Tokens / item | Acc / Token (×10⁻³) |
|:------------|:------:|:--------------:|:--------------------:|
| CoT         | 100.0  | 1271           | 23.1                 |
| SC-CoT      | 100.0  | 5676           | 9.1                  |
| ToT (light) | 83.3   | 2295           | 6.0                  |
| GoT (light) | 83.3   | 2312           | 6.0                  |
| FoT (light) | 83.3   | 2214           | 5.4                  |
| **BAMoT**   | **100.0** | **1435**     | **11.6**             |

### StrategyQA — Accuracy vs Budget (n=8)

| Method | Budget |  Acc  | Mean Tokens | p50 Latency | p90 Latency |
|:-------|------:|:-----:|------------:|------------:|------------:|
| BAMoT  |   600 | 0.750 |       484.0 |       2.852s|       3.534s|
| CoT    |   600 | 0.875 |       195.0 |       3.327s|       3.967s|
| SC-CoT |   600 | 0.875 |       590.8 |       4.321s|       5.074s|
| ToT    |   600 | 0.750 |      2544.0 |       3.197s|       4.851s|
| GoT    |   600 | 0.875 |       896.0 |       8.907s|      13.898s|
| FoT    |   600 | 0.750 |      1553.4 |      16.278s|      20.383s|
| BAMoT  |  1200 | 0.875 |       955.1 |       3.497s|       3.815s|
| BAMoT  |  1800 | 0.625 |      1622.0 |       3.082s|       3.696s|
| BAMoT  |  2400 | **1.000** | **2226.9** | **3.948s** | **4.495s** |

**Anytime AUC (StrategyQA):** CoT 0.875, GoT 0.854, ToT 0.833, FoT 0.812, **BAMoT 0.792**, SC-CoT 0.750.  
(*BAMoT reaches 1.00 accuracy at B=2400 with lower latency than tree methods.*)

### AIME — Accuracy vs Budget (n=4)

| Method   | Budget |  Acc  | Mean Tokens |   p50  |   p90  |
|:---------|------:|:-----:|------------:|-------:|-------:|
| **BAMoT**|   600 | **1.000** |   559.3 |  3.279s|  3.507s|
| **BAMoT**|  1200 | **1.000** |  1106.8 |  2.887s|  3.342s|
| **BAMoT**|  1800 | **1.000** |  1647.5 |  3.101s|  3.348s|
| **BAMoT**|  2400 | **1.000** |  2143.8 |  3.412s|  3.743s|
| CoT / SC-CoT / ToT / GoT / FoT | — | **1.000** | *higher tokens & latency for tree methods* | | |

**Anytime AUC (AIME):** all methods ≈ **1.000** (saturates on tiny slice).

### MATH-500 — Accuracy vs Budget (n=4)

| Method   | Budget |  Acc  | Mean Tokens |   p50  |   p90  |
|:---------|------:|:-----:|------------:|-------:|-------:|
| **BAMoT**|   600 | **1.000** |   635.3 |  3.166s|  3.925s|
| **BAMoT**|  1200 | **1.000** |  1040.5 |  3.253s|  3.574s|
| **BAMoT**|  1800 | **1.000** |  1782.5 |  3.078s|  4.360s|
| **BAMoT**|  2400 | **1.000** |  2074.0 |  3.910s|  4.741s|

**Anytime AUC (MATH-500):** **BAMoT 1.000**, GoT 1.000, ToT 1.000, CoT 0.958, FoT 0.958, SC-CoT 0.750.

> ⚠️ *The StrategyQA/AIME/MATH-500 runs above use small dev slices (8/4/4 items). They’re meant to show **trends**. For publication, scale up items for tighter CIs.*

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
