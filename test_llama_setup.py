#!/usr/bin/env python3
"""
Quick test script to verify LLaMA setup is ready.
"""

import os
import sys

def test_llama_setup():
    print("="*60)
    print("LLaMA Setup Test")
    print("="*60)
    print()
    
    # 1. Check if llama-cpp-python is installed
    print("1. Checking llama-cpp-python installation...")
    try:
        import llama_cpp
        print("   ✅ llama-cpp-python is installed")
        print(f"   Version: {llama_cpp.__version__ if hasattr(llama_cpp, '__version__') else 'unknown'}")
    except ImportError:
        print("   ❌ llama-cpp-python is NOT installed")
        print("   Install with: pip install llama-cpp-python")
        print("   (Note: This may take a while and requires compilation)")
        return False
    print()
    
    # 2. Check if model path is set
    print("2. Checking model path...")
    model_path = os.getenv("LLAMA_MODEL_PATH", "")
    if model_path:
        print(f"   ✅ LLAMA_MODEL_PATH is set: {model_path}")
        if os.path.exists(model_path):
            print(f"   ✅ Model file exists: {os.path.getsize(model_path) / (1024**3):.2f} GB")
        else:
            print(f"   ⚠️  Model file not found at: {model_path}")
            return False
    else:
        print("   ⚠️  LLAMA_MODEL_PATH not set")
        print("   Set with: export LLAMA_MODEL_PATH=/path/to/model.gguf")
        print("   Or use: --llama_model_path /path/to/model.gguf")
        return False
    print()
    
    # 3. Test ModelGateway initialization
    print("3. Testing ModelGateway with LLaMA backend...")
    try:
        from utils.model_gateway import ModelGateway
        gw = ModelGateway(
            model="llama",
            backend="llama_cpp",
            llama_model_path=model_path,
            llama_ctx=2048,
        )
        print("   ✅ ModelGateway initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        return False
    print()
    
    # 4. Test a simple chat
    print("4. Testing a simple chat...")
    try:
        result = gw.chat(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello, LLaMA is working!'"
        )
        print(f"   ✅ Chat successful!")
        print(f"   Response: {result['text'][:100]}...")
        print(f"   Tokens: {result['usage'].get('prompt_tokens', 'N/A')} prompt + {result['usage'].get('completion_tokens', 'N/A')} completion")
        print(f"   Latency: {result.get('latency', 0):.2f}s")
    except Exception as e:
        print(f"   ❌ Chat failed: {e}")
        return False
    print()
    
    print("="*60)
    print("✅ All tests passed! LLaMA is ready to use.")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_llama_setup()
    sys.exit(0 if success else 1)

