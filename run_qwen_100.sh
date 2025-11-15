#!/bin/bash
# Run all methods on Qwen for Game24 (100 items)

set -e
cd "$(dirname "$0")"

QWEN_MODEL_PATH="$(pwd)/models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
export QWEN_MODEL_PATH

echo "=== Running all methods on Qwen (Game24, 100 items) ==="
echo "Model: $QWEN_MODEL_PATH"
echo ""

# 1. BAMoT
echo "1. BAMoT - Game24 (100 items)..."
python3 run.py \
    --backend llama_cpp \
    --llama_model_path "$QWEN_MODEL_PATH" \
    --method bamot \
    --dataset game24 \
    --budget_tokens 1800 \
    --seeds 3 \
    --bamot_seed_tokens 100 \
    --bamot_refine_tokens 300 \
    --limit 100 \
    --exp_name bamot_g24_qwen_100

# 2. CoT
echo "2. CoT - Game24 (100 items)..."
python3 run.py \
    --backend llama_cpp \
    --llama_model_path "$QWEN_MODEL_PATH" \
    --method cot \
    --dataset game24 \
    --limit 100 \
    --exp_name cot_g24_qwen_100

# 3. SC-CoT
echo "3. SC-CoT - Game24 (100 items)..."
python3 run.py \
    --backend llama_cpp \
    --llama_model_path "$QWEN_MODEL_PATH" \
    --method sc_cot \
    --dataset game24 \
    --sc_samples 5 \
    --limit 100 \
    --exp_name sc_cot_g24_qwen_100

# 4. ToT
echo "4. ToT - Game24 (100 items)..."
python3 run.py \
    --backend llama_cpp \
    --llama_model_path "$QWEN_MODEL_PATH" \
    --method tot \
    --dataset game24 \
    --tot_branch 2 \
    --tot_depth 2 \
    --limit 100 \
    --exp_name tot_g24_qwen_100

# 5. GoT
echo "5. GoT - Game24 (100 items)..."
python3 run.py \
    --backend llama_cpp \
    --llama_model_path "$QWEN_MODEL_PATH" \
    --method got \
    --dataset game24 \
    --got_beam 2 \
    --got_steps 2 \
    --limit 100 \
    --exp_name got_g24_qwen_100

# 6. FoT
echo "6. FoT - Game24 (100 items)..."
python3 run.py \
    --backend llama_cpp \
    --llama_model_path "$QWEN_MODEL_PATH" \
    --method fot \
    --dataset game24 \
    --fot_trees 3 \
    --fot_branch 2 \
    --fot_depth 1 \
    --limit 100 \
    --exp_name fot_g24_qwen_100

echo ""
echo "=== All Qwen experiments completed! ==="

