# BAMoT Experimental Scaffold (Minimal, Colab‑Ready)

This repo gives you a **tiny but working** harness to compare:
- CoT (single chain)
- SC‑CoT (self‑consistency voting)
- BAMoT (very light mesh + budgeted expansions)

**Datasets (toy):** GSM8K (5 samples) to validate the pipeline end‑to‑end.  
You can plug in Game24, MATH‑500, AIME, StrategyQA later.

---

## Quick Start (Colab / Local)

1) **Upload** this zip to Colab and unzip:

```bash
!unzip -o bamot_exp.zip -d bamot_exp && cd bamot_exp
```

2) **Install deps**:
```bash
%pip install -q -r requirements.txt
```

3) **Set your API key** (OpenAI):
```bash
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
```

4) **Run** (toy GSM8K set, 5 items):
```bash
!python run.py --method bamot --dataset gsm8k --budget_tokens 800 --seeds 4 --exp_name demo_bamot
!python run.py --method cot   --dataset gsm8k --budget_tokens 800 --exp_name demo_cot
!python run.py --method sc_cot --dataset gsm8k --budget_tokens 800 --sc_samples 5 --exp_name demo_sc_cot
```

5) **See results**:
- CSV at `results/<exp_name>.csv` (accuracy, tokens, latency)
- Logs at `logs/<exp_name>.log`

---

## What’s inside

```
bamot_exp/
 ├─ run.py                   # CLI runner, unified evaluation loop
 ├─ requirements.txt
 ├─ prompts/
 │   ├─ cot_prompt.txt       # CoT system/user templates
 │   ├─ answer_extract.txt   # Regex guidance for answer extraction
 ├─ methods/
 │   ├─ cot.py               # Single Chain‑of‑Thought
 │   ├─ sc_cot.py            # Self‑Consistency (vote)
 │   └─ bamot.py             # Budget‑Aware Mesh‑of‑Thoughts (minimal)
 ├─ loaders/
 │   └─ gsm8k.py             # Tiny 5‑sample GSM8K subset
 └─ utils/
     ├─ model_gateway.py     # OpenAI chat wrapper (simple)
     ├─ tokens.py            # Token estimation via tiktoken (fallback to char count)
     ├─ logger.py            # CSV logging, timers
     └─ evals.py             # Answer parse + exact match for GSM8K‑style numbers
```

> **Note**: This is intentionally minimal. The BAMoT here implements: diversified seeding → cheap triage → budgeted selective expansion → consensus. Merging is approximated by de‑duplication of equivalent states; you can swap in richer merge heuristics later.

---

## Extend later

- Add datasets: Game24, MATH‑500, AIME, StrategyQA (see `loaders/`).
- Add baselines: ToT, GoT, FoT (skeletons similar to `methods/`).
- Add ablations: disable merging, scheduler, triage, consensus via flags.
- Replace token estimator with model‑reported usage if you prefer.
- Persist per‑sample traces to inspect reasoning **per item**.
