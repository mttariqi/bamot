#!/bin/bash
# Quick setup script to set LLaMA model path

MODEL_DIR="$(cd "$(dirname "$0")" && pwd)/models"
MODEL_FILE="$MODEL_DIR/llama-3.2-1b-instruct-q4_k_m.gguf"

if [ -f "$MODEL_FILE" ]; then
    export LLAMA_MODEL_PATH="$MODEL_FILE"
    echo "✅ LLAMA_MODEL_PATH set to: $LLAMA_MODEL_PATH"
    echo ""
    echo "To use in current session:"
    echo "  export LLAMA_MODEL_PATH=\"$MODEL_FILE\""
    echo ""
    echo "To make permanent, add to ~/.zshrc or ~/.bashrc:"
    echo "  export LLAMA_MODEL_PATH=\"$MODEL_FILE\""
else
    echo "⚠️  Model file not found: $MODEL_FILE"
    echo "   Please wait for download to complete or download manually."
fi

