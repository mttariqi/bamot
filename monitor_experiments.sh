#!/bin/bash
# Monitor 50-item experiment progress

echo "=== 50-Item Experiment Monitor ==="
echo

echo "Running processes:"
ps aux | grep "python3 run.py" | grep -v grep | wc -l
echo

echo "Completed result files:"
ls -1 results/*_50.csv 2>/dev/null | wc -l
echo

echo "Result files:"
ls -lh results/*_50.csv 2>/dev/null | tail -10
echo

echo "To check detailed progress, run:"
echo "  tail -f logs/*.log"
echo
echo "To compare results when done, run:"
echo "  python3 compare_50_results.py"

