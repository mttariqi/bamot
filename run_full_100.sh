#!/bin/bash
# Run full 100-item experiments with resume capability
# This script will automatically skip already-completed items

set -e

echo "=========================================="
echo "Running Full 100-Item Experiments"
echo "=========================================="
echo "Note: Will automatically resume from existing results"
echo

cd "$(dirname "$0")"

# StrategyQA - Full 100 items
echo "=== StrategyQA (100 items) ==="
echo "BAMoT..."
python3 run.py --method bamot --dataset strategyqa --budget_tokens 1200 --seeds 2 --limit 100 --exp_name bamot_sqa_100

echo "CoT..."
python3 run.py --method cot --dataset strategyqa --limit 100 --exp_name cot_sqa_100

echo "SC-CoT..."
python3 run.py --method sc_cot --dataset strategyqa --sc_samples 5 --limit 100 --exp_name sc_cot_sqa_100

# Game24 - Full 100 items
echo ""
echo "=== Game24 (100 items) ==="
echo "BAMoT..."
python3 run.py --method bamot --dataset game24 --budget_tokens 1800 --seeds 3 --bamot_seed_tokens 100 --bamot_refine_tokens 300 --limit 100 --exp_name bamot_g24_100

echo "ToT..."
python3 run.py --method tot --dataset game24 --tot_branch 2 --tot_depth 2 --limit 100 --exp_name tot_g24_100

echo "GoT..."
python3 run.py --method got --dataset game24 --got_beam 2 --got_steps 2 --limit 100 --exp_name got_g24_100

echo "FoT..."
python3 run.py --method fot --dataset game24 --fot_trees 3 --fot_branch 2 --fot_depth 1 --limit 100 --exp_name fot_g24_100

echo ""
echo "=========================================="
echo "All experiments complete!"
echo "=========================================="
echo "Run 'python3 combine_results.py' to merge 50-item and 100-item results"
echo "Run 'python3 compare_100_results.py' to see full comparison"

