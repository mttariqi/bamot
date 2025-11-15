#!/bin/bash
# Helper script to set OpenAI API key

echo "=========================================="
echo "OpenAI API Key Setup"
echo "=========================================="
echo ""

# Check if already set
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ API Key is already set!"
    echo "Length: ${#OPENAI_API_KEY} characters"
    echo "First 10 chars: $(echo $OPENAI_API_KEY | head -c 10)..."
    echo ""
    echo "To verify it works, run: python3 test_smoke.py"
    exit 0
fi

echo "To set your API key, you have two options:"
echo ""
echo "OPTION 1: Set for current session only"
echo "  export OPENAI_API_KEY='sk-your-key-here'"
echo ""
echo "OPTION 2: Set permanently (add to ~/.zshrc)"
echo "  echo \"export OPENAI_API_KEY='sk-your-key-here'\" >> ~/.zshrc"
echo "  source ~/.zshrc"
echo ""
echo "After setting, verify with:"
echo "  echo \$OPENAI_API_KEY | head -c 20"
echo ""

# Try to read from a file if it exists
if [ -f ".env" ]; then
    echo "Found .env file, checking for OPENAI_API_KEY..."
    source .env 2>/dev/null
    if [ -n "$OPENAI_API_KEY" ]; then
        echo "✅ Loaded from .env file!"
        export OPENAI_API_KEY
    fi
fi

