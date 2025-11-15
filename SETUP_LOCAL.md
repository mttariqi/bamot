# Local Setup Guide for BAMoT

## Quick Start

### 1. Install Dependencies
```bash
cd /Users/mac/MS-AI/thesis/bamot
pip install -r requirements.txt
```

### 2. Set OpenAI API Key

**Option A: Environment Variable (Recommended)**
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Option B: Create .env file (if using python-dotenv)**
```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

**Option C: For persistent setup (macOS/Linux)**
Add to `~/.zshrc` or `~/.bashrc`:
```bash
export OPENAI_API_KEY="sk-your-key-here"
source ~/.zshrc  # or ~/.bashrc
```

### 3. Verify Setup
```bash
python3 -c "import os; print('API Key set:', bool(os.getenv('OPENAI_API_KEY')))"
```

Should output: `API Key set: True`

---

## Running Experiments

### Basic Test Run
```bash
python3 run.py --method bamot --dataset game24 \
  --budget_tokens 1200 --seeds 2 \
  --bamot_seed_tokens 80 --bamot_refine_tokens 256 \
  --limit 5 --exp_name test_run
```

### Full Experiment (StrategyQA)
```bash
python3 run.py --method bamot --dataset strategyqa \
  --budget_tokens 2400 --seeds 2 \
  --bamot_seed_tokens 80 --bamot_refine_tokens 256 \
  --exp_name bamot_sqa_B2400
```

### Budget Sweep (Bash)
```bash
for B in 600 1200 1800 2400; do
  python3 run.py --method bamot --dataset strategyqa \
    --budget_tokens $B --seeds 2 \
    --bamot_seed_tokens 80 --bamot_refine_tokens 256 \
    --exp_name bamot_sqa_B${B}
done
```

### Running with Local LLaMA Models (llama.cpp backend)

You can now swap GPT-4o-mini for a local LLaMA-style model served via [llama.cpp](https://github.com/ggerganov/llama.cpp). Steps:

1. Install the optional dependency:
   ```bash
   pip install llama-cpp-python
   ```
2. Download (or convert) a GGUF model file, e.g., `Llama-3-8B-Instruct.Q4_K_M.gguf`.
3. Point the runner at that file:
   ```bash
   export LLAMA_MODEL_PATH=/absolute/path/to/Llama-3-8B-Instruct.Q4_K_M.gguf
   # or pass --llama_model_path explicitly
   ```
4. Run any experiment with the new backend:
   ```bash
   python3 run.py --backend llama_cpp \
     --method bamot --dataset strategyqa \
     --limit 5 --exp_name bamot_sqa_llama
   ```

Optional knobs:
- `--llama_ctx` – context window (default 4096)
- `--llama_threads` – CPU threads (default auto)

All prompting, budgeting, and evaluation code remains unchanged.

---

## Troubleshooting

### "OPENAI_API_KEY not set" Error
- Check: `echo $OPENAI_API_KEY`
- If empty, set it: `export OPENAI_API_KEY="sk-..."`
- For persistent setup, add to shell config file

### "Module not found" Errors
```bash
pip install --upgrade -r requirements.txt
```

### Rate Limiting
- Add delays between calls if hitting rate limits
- Consider using `--limit` to test on smaller subsets first

### Token Budget Issues
- Verify budget is being enforced: check `results/*.csv` for `prompt_toks + completion_toks`
- Should be ≤ `budget_tokens` per item

---

## Differences from Colab

1. **No GPU needed:** API calls are the bottleneck, not local compute
2. **Environment variables:** Must set `OPENAI_API_KEY` manually
3. **File paths:** Use absolute or relative paths (Colab uses `/content/`)
4. **Results location:** Check `./results/` directory (same as Colab)

---

## Recommended Workflow

1. **Test on small subset:**
   ```bash
   python3 run.py --method bamot --dataset game24 \
     --budget_tokens 1200 --limit 3 --exp_name test
   ```

2. **Check results:**
   ```bash
   cat results/test.csv
   ```

3. **Run full experiment:**
   ```bash
   python3 run.py --method bamot --dataset game24 \
     --budget_tokens 1200 --exp_name bamot_g24_B1200
   ```

4. **Plot results:**
   ```bash
   python3 plot_results.py
   ```

---

## Performance Notes

- **Latency:** Depends on API response time (typically 2-5s per item)
- **Cost:** ~$0.01-0.05 per 1000 tokens (gpt-4o-mini)
- **Budget 1200 tokens:** ~$0.01-0.02 per item
- **100 items:** ~$1-2 total cost

---

## Next Steps

1. Run a small test to verify setup
2. Check `FIXES_SUMMARY.md` for recent bug fixes
3. Review `README.md` for full documentation
4. Run your experiments!

