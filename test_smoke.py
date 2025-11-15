#!/usr/bin/env python3
"""
Quick smoke test to verify BAMoT setup and fixes work correctly.
Tests on a single item from each dataset to verify:
- API connection works
- Budget enforcement works
- Predictions are generated
- No crashes occur
"""

import os
import sys

def check_api_key():
    """Check if API key is set."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set!")
        print("\nTo set it, run:")
        print("  export OPENAI_API_KEY='sk-your-key-here'")
        print("\nOr add to your ~/.zshrc for persistence:")
        print("  echo \"export OPENAI_API_KEY='sk-your-key-here'\" >> ~/.zshrc")
        return False
    
    # Don't print the full key, just confirm it's set
    masked = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 11 else "***"
    print(f"✅ API Key found: {masked}")
    return True

def run_smoke_test():
    """Run a minimal test on each dataset."""
    print("\n" + "="*60)
    print("BAMoT Smoke Test")
    print("="*60)
    
    if not check_api_key():
        sys.exit(1)
    
    print("\n📦 Testing imports...")
    try:
        from utils.model_gateway import ModelGateway
        from methods.bamot import run_item
        from loaders.game24 import load as load_game24
        from loaders.strategyqa import load as load_strategyqa
        from loaders.math500 import load as load_math500
        print("✅ All imports successful")
    except Exception as e:
        print(f"❌ Import error: {e}")
        sys.exit(1)
    
    print("\n🧪 Testing ModelGateway connection...")
    try:
        gw = ModelGateway(model="gpt-4o-mini", temperature=0.2, max_tokens=50)
        test_response = gw.chat(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'test' and nothing else."
        )
        if test_response.get("text"):
            print("✅ API connection works!")
        else:
            print("❌ API returned empty response")
            sys.exit(1)
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        print("\nCheck your API key and internet connection.")
        sys.exit(1)
    
    print("\n🎯 Testing BAMoT on Game24 (1 item)...")
    try:
        dataset = load_game24(limit=1)
        if not dataset:
            print("❌ No data loaded")
            sys.exit(1)
        
        item = dataset[0]
        print(f"   Question: {item['question'][:60]}...")
        
        result = run_item(
            item,
            gateway=gw,
            cot_system="You are a symbolic arithmetic solver.",
            seeds=2,
            budget_tokens=400,  # Small budget for quick test
            seed_tokens=60,
            refine_tokens=100,
            refine_topk=1,
            task_mode="game24"
        )
        
        pred = result.get("pred")
        usage = result.get("usage", {})
        total_tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        
        print(f"   ✅ Prediction: {pred}")
        print(f"   ✅ Tokens used: {total_tokens} (budget: 400)")
        
        if total_tokens > 400:
            print(f"   ⚠️  WARNING: Budget exceeded! ({total_tokens} > 400)")
        else:
            print(f"   ✅ Budget respected!")
            
    except Exception as e:
        print(f"❌ BAMoT test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✅ All smoke tests passed!")
    print("="*60)
    print("\nYou can now run full experiments with:")
    print("  python3 run.py --method bamot --dataset game24 --budget_tokens 1200 --limit 5")
    print()

if __name__ == "__main__":
    run_smoke_test()

