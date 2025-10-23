from typing import List, Dict, Optional

# Minimal dev split (8 items). Gold labels are "yes"/"no".
_DEV: List[Dict] = [
    {"id": "sqa-001", "question": "Do camels live in deserts?", "answer": "yes"},
    {"id": "sqa-002", "question": "Is marble a type of metal?", "answer": "no"},
    {"id": "sqa-003", "question": "Do penguins naturally live at the North Pole?", "answer": "no"},
    {"id": "sqa-004", "question": "Can humans breathe underwater without equipment?", "answer": "no"},
    {"id": "sqa-005", "question": "Is Jupiter a planet?", "answer": "yes"},
    {"id": "sqa-006", "question": "Do spiders have six legs?", "answer": "no"},
    {"id": "sqa-007", "question": "Is chocolate made from cacao beans?", "answer": "yes"},
    {"id": "sqa-008", "question": "Do bats lay eggs?", "answer": "no"},
]

def load(split: str = "dev", limit: Optional[int] = None) -> List[Dict]:
    if split != "dev":
        raise NotImplementedError("StrategyQA full split will be plugged later.")
    data = _DEV if limit is None else _DEV[:limit]
    # Standardized fields expected by the harness
    return [{"id": ex["id"], "question": ex["question"], "answer": ex["answer"], "meta": {"dataset": "strategyqa"}} for ex in data]
