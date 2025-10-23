from typing import List, Dict, Optional

# Tiny dev split for smoke tests (answers are integers)
_DEV: List[Dict] = [
    {"id": "aime-001", "question": "If 2x + 3 = 13, what is x?", "answer": "5"},
    {"id": "aime-002", "question": "Compute the value of 7^2 - 3^2.", "answer": "40"},
    {"id": "aime-003", "question": "If a*b = a + b + ab, compute 2*3.", "answer": "11"},
    {"id": "aime-004", "question": "The sum of interior angles of a hexagon (in degrees) equals?", "answer": "720"},
]

def load(split: str = "dev", limit: Optional[int] = None) -> List[Dict]:
    if split != "dev":
        raise NotImplementedError("AIME full split will be plugged later.")
    data = _DEV if limit is None else _DEV[:limit]
    # Standardized fields expected by your harness
    return [
        {"id": ex["id"], "question": ex["question"], "answer": ex["answer"], "meta": {"dataset": "aime"}}
        for ex in data
    ]
