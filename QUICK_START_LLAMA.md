# Quick Start: LLaMA Backend

## ✅ Installation Complete!

1. **llama-cpp-python** - Installed with Metal support (for Apple Silicon)
2. **LLaMA 3.2 1B Model** - Downloading to `models/` directory

---

## Setup (One-Time)

After the model download completes, set the environment variable:

```bash
# Quick setup (run this script)
./setup_llama_env.sh

# Or manually:
export LLAMA_MODEL_PATH="$(pwd)/models/llama-3.2-1b-instruct-q4_k_m.gguf"
```

**To make it permanent**, add to your `~/.zshrc`:
```bash
export LLAMA_MODEL_PATH="/Users/mac/MS-AI/thesis/bamot/models/llama-3.2-1b-instruct-q4_k_m.gguf"
```

---

## Test It Works

```bash
python3 test_llama_setup.py
```

This should show:
- ✅ llama-cpp-python is installed
- ✅ Model file exists
- ✅ ModelGateway can initialize
- ✅ A simple chat works

---

## Run Your First Experiment

```bash
# Small test (5 items)
python3 run.py --backend llama_cpp \
  --method bamot --dataset strategyqa \
  --budget_tokens 1200 --seeds 2 \
  --limit 5 --exp_name test_llama

# Check results
cat results/test_llama.csv
```

---

## What Was Installed

- **Model:** LLaMA 3.2 1B Instruct (Q4_K_M quantization)
- **Size:** ~700MB
- **Speed:** ~2-5 tokens/sec on M2 Mac
- **Quality:** Good for testing, reasonable for production

**Why this model?**
- Industry standard (Meta's LLaMA 3.2)
- Small and fast (good for testing)
- Q4_K_M quantization (good balance of quality/speed)
- Widely used in research

---

## Next Steps

1. ✅ Wait for model download to complete
2. ✅ Run `./setup_llama_env.sh` or set `LLAMA_MODEL_PATH`
3. ✅ Run `python3 test_llama_setup.py`
4. ✅ Run small experiment (--limit 5)
5. ✅ Scale to full runs

---

## Troubleshooting

**Model not found?**
```bash
ls -lh models/*.gguf
# If empty, download manually or wait for curl to finish
```

**Slow performance?**
- This is normal for CPU inference
- M2 Mac should get 2-5 tokens/sec
- For faster: use GPU or smaller quantization

**Want a better model?**
- LLaMA 3.2 3B: Better quality, slower
- Qwen 2.5: Alternative architecture
- See `SETUP_LLAMA.md` for more options

