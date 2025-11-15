# LLaMA Backend Setup Guide

## Status: ✅ Code Ready, ⚠️ Needs Installation

The LLaMA backend is fully implemented and ready to use. You just need to:

1. Install `llama-cpp-python`
2. Download a LLaMA model file (.gguf format)
3. Set the model path

---

## Step 1: Install llama-cpp-python

```bash
pip install llama-cpp-python
```

**Note:** This may take 5-10 minutes as it compiles C++ code. If you have issues:

```bash
# For Apple Silicon (M1/M2/M3):
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python

# For CUDA (if you have NVIDIA GPU):
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python

# For CPU only (slower but works everywhere):
pip install llama-cpp-python
```

---

## Step 2: Download a LLaMA Model

You need a model in **GGUF format**. Recommended models:

### Option A: LLaMA 3.2 1B (Small, Fast)
```bash
# Download from HuggingFace (example)
wget https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf
```

### Option B: LLaMA 3.2 3B (Better Quality)
```bash
wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf
```

### Option C: Qwen 2.5 (Alternative)
```bash
wget https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

**Recommendation:** Start with LLaMA 3.2 1B (Q4_K_M quantization) for fast testing.

---

## Step 3: Set Model Path

```bash
export LLAMA_MODEL_PATH=/path/to/your/model.gguf
```

Or use the `--llama_model_path` argument when running.

---

## Step 4: Test Setup

```bash
python3 test_llama_setup.py
```

This will verify:
- ✅ llama-cpp-python is installed
- ✅ Model file exists
- ✅ ModelGateway can initialize
- ✅ A simple chat works

---

## Step 5: Run Experiments

Once setup is verified, run experiments with:

```bash
# StrategyQA with LLaMA
python3 run.py --backend llama_cpp \
  --method bamot --dataset strategyqa \
  --budget_tokens 1200 --seeds 2 \
  --limit 10 --exp_name bamot_sqa_llama

# Game24 with LLaMA
python3 run.py --backend llama_cpp \
  --method bamot --dataset game24 \
  --budget_tokens 1800 --seeds 3 \
  --limit 10 --exp_name bamot_g24_llama
```

---

## Configuration Options

```bash
--backend llama_cpp              # Use LLaMA backend
--llama_model_path PATH         # Path to .gguf file
--llama_ctx 4096                 # Context window size (default: 4096)
--llama_threads 4                # CPU threads (default: auto)
```

---

## Troubleshooting

### "llama-cpp-python not found"
```bash
pip install llama-cpp-python
```

### "No LLaMA model path provided"
Set `LLAMA_MODEL_PATH` or use `--llama_model_path`:
```bash
export LLAMA_MODEL_PATH=/path/to/model.gguf
```

### "Model file not found"
Check the path is correct:
```bash
ls -lh $LLAMA_MODEL_PATH
```

### Slow performance
- Use a smaller model (1B instead of 3B)
- Use Q4_K_M quantization (not Q8 or F16)
- Increase `--llama_threads` if you have many CPU cores
- Consider GPU acceleration (see Step 1)

### Out of memory
- Use a smaller model
- Reduce `--llama_ctx` (e.g., 2048 instead of 4096)
- Use lower quantization (Q4_K_M instead of Q8)

---

## Performance Expectations

- **LLaMA 3.2 1B (Q4_K_M):** ~2-5 tokens/sec on CPU
- **LLaMA 3.2 3B (Q4_K_M):** ~1-3 tokens/sec on CPU
- **With GPU (Metal/CUDA):** 10-50x faster

For 100-item experiments, expect:
- **StrategyQA:** 5-15 minutes (vs 1-2 minutes with OpenAI API)
- **Game24:** 15-30 minutes (vs 2-5 minutes with OpenAI API)

---

## Next Steps

1. ✅ Install llama-cpp-python
2. ✅ Download a model file
3. ✅ Run `test_llama_setup.py`
4. ✅ Run small experiments (--limit 5)
5. ✅ Scale to full 100-item runs

---

**Ready to test?** Run `python3 test_llama_setup.py` after installation!

