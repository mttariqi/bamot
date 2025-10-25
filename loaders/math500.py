from typing import List, Dict, Optional

# Tiny dev split for smoke tests (keep answers as integers for now)
_DEV: List[Dict] = [
    {"id": "m500-001", "question": "Compute 15 * 14.", "answer": "210"},
    {"id": "m500-002", "question": "Solve for x: 3x - 5 = 16.", "answer": "7"},
    {"id": "m500-003", "question": "What is the GCD of 60 and 42?", "answer": "6"},
    {"id": "m500-004", "question": "What is 12^2 - 8^2?", "answer": "80"},
]

def load(split: str = "dev", limit: Optional[int] = None) -> List[Dict]:
    if split != "dev":
        raise NotImplementedError("MATH-500 full split will be plugged later.")
    data = _DEV if limit is None else _DEV[:limit]
    return [
        {"id": ex["id"], "question": ex["question"], "answer": ex["answer"], "meta": {"dataset": "math500"}}
        for ex in data
    ]
